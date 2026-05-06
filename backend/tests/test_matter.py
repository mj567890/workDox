"""Tests for matter service and workflow operations."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def seed_matter_data(db_session: AsyncSession):
    """Seed data needed for matter tests."""
    from app.models.user import User
    from app.models.role import Role
    from app.models.document import MatterType
    from app.core.security import hash_password

    roles = [
        Role(id=1, role_name="管理员", role_code="admin"),
        Role(id=3, role_name="事项负责人", role_code="matter_owner"),
    ]
    db_session.add_all(roles)
    await db_session.flush()

    admin = User(
        id=1, username="admin", password_hash=hash_password("admin123"),
        real_name="管理员", status="active",
    )
    admin.roles.append(roles[0])
    db_session.add(admin)

    owner = User(
        id=3, username="owner", password_hash=hash_password("owner123"),
        real_name="事项负责人", status="active",
    )
    owner.roles.append(roles[1])
    db_session.add(owner)

    mt = MatterType(id=1, name="招生工作", code="enrollment", description="招生相关工作")
    db_session.add(mt)
    await db_session.commit()


class TestMatterService:
    async def test_create_matter(self, db_session, seed_matter_data):
        from app.services.matter_service import matter_service
        from pydantic import BaseModel
        from datetime import datetime, timezone

        class MatterCreate(BaseModel):
            title: str
            type_id: int
            owner_id: int
            member_ids: list[int] = []
            is_key_project: bool = False
            due_date: datetime | None = None
            description: str | None = None

        matter = await matter_service.create_matter(
            db_session,
            MatterCreate(
                title="2026年秋季招生计划",
                type_id=1,
                owner_id=1,
                member_ids=[3],
                is_key_project=True,
                due_date=datetime(2026, 12, 31, tzinfo=timezone.utc),
                description="制定秋季招生计划方案",
            ),
            user_id=1,
        )
        assert matter.title == "2026年秋季招生计划"
        assert matter.matter_no is not None
        assert matter.status == "pending"
        assert matter.is_key_project is True

    async def test_update_matter(self, db_session, seed_matter_data):
        from app.services.matter_service import matter_service
        from pydantic import BaseModel

        class MatterCreate(BaseModel):
            title: str
            type_id: int
            owner_id: int
            member_ids: list[int] = []
            is_key_project: bool = False
            due_date: datetime | None = None
            description: str | None = None

        m = await matter_service.create_matter(
            db_session,
            MatterCreate(title="测试事项", type_id=1, owner_id=1),
            user_id=1,
        )

        class MatterUpdate(BaseModel):
            title: str | None = None

        updated = await matter_service.update_matter(
            db_session, m.id, MatterUpdate(title="更新后的事项名称"),
            {"id": 1, "roles": ["admin"]},
        )
        assert updated.title == "更新后的事项名称"

    async def test_delete_matter(self, db_session, seed_matter_data):
        from app.services.matter_service import matter_service
        from app.core.exceptions import ForbiddenException
        from pydantic import BaseModel

        class MatterCreate(BaseModel):
            title: str
            type_id: int
            owner_id: int
            member_ids: list[int] = []
            is_key_project: bool = False
            due_date: datetime | None = None
            description: str | None = None

        m = await matter_service.create_matter(
            db_session,
            MatterCreate(title="待删除事项", type_id=1, owner_id=1),
            user_id=1,
        )

        # Non-owner cannot delete
        with pytest.raises(ForbiddenException):
            await matter_service.delete_matter(
                db_session, m.id, {"id": 3, "roles": ["matter_owner"]},
            )

        # Owner can delete
        result = await matter_service.delete_matter(
            db_session, m.id, {"id": 1, "roles": ["admin"]},
        )
        assert result is True

    async def test_add_member(self, db_session, seed_matter_data):
        from app.services.matter_service import matter_service
        from pydantic import BaseModel

        class MatterCreate(BaseModel):
            title: str
            type_id: int
            owner_id: int
            member_ids: list[int] = []
            is_key_project: bool = False
            due_date: datetime | None = None
            description: str | None = None

        m = await matter_service.create_matter(
            db_session,
            MatterCreate(title="成员测试", type_id=1, owner_id=1),
            user_id=1,
        )

        class MemberAdd(BaseModel):
            user_ids: list[int]
            role_in_matter: str = "collaborator"

        result = await matter_service.add_members(
            db_session, m.id, MemberAdd(user_ids=[3]),
            {"id": 1, "roles": ["admin"]},
        )
        assert len(result) == 1

    async def test_add_comment(self, db_session, seed_matter_data):
        from app.services.matter_service import matter_service, matter_comment_service
        from pydantic import BaseModel

        class MatterCreate(BaseModel):
            title: str
            type_id: int
            owner_id: int
            member_ids: list[int] = []
            is_key_project: bool = False
            due_date: datetime | None = None
            description: str | None = None

        m = await matter_service.create_matter(
            db_session,
            MatterCreate(title="评论测试", type_id=1, owner_id=1),
            user_id=1,
        )

        comment = await matter_comment_service.add_comment(
            db_session, m.id, user_id=1, content="这条需要加快进度",
        )
        assert comment.content == "这条需要加快进度"
        assert comment.user_id == 1

    async def test_get_comments(self, db_session, seed_matter_data):
        from app.services.matter_service import matter_service, matter_comment_service
        from app.core.pagination import PaginationParams
        from pydantic import BaseModel

        class MatterCreate(BaseModel):
            title: str
            type_id: int
            owner_id: int
            member_ids: list[int] = []
            is_key_project: bool = False
            due_date: datetime | None = None
            description: str | None = None

        m = await matter_service.create_matter(
            db_session,
            MatterCreate(title="多评论测试", type_id=1, owner_id=1),
            user_id=1,
        )
        await matter_comment_service.add_comment(db_session, m.id, 1, "第一条评论")
        await matter_comment_service.add_comment(db_session, m.id, 3, "第二条评论")

        comments, total = await matter_comment_service.get_comments(
            db_session, m.id, PaginationParams(limit=50),
        )
        assert len(comments) == 2
        assert total == 2


class TestWorkflowTemplate:
    async def test_create_template(self, db_session, seed_matter_data):
        from app.services.workflow_service import WorkflowService
        from pydantic import BaseModel
        from types import SimpleNamespace

        class NodeDef(BaseModel):
            node_name: str
            node_order: int
            owner_role: str
            sla_hours: int | None = None
            required_documents_rule: dict | None = None
            description: str | None = None

        class TemplateCreate(BaseModel):
            name: str
            matter_type_id: int
            is_active: bool = True
            description: str | None = None
            nodes: list[NodeDef] = []

        nodes = [
            NodeDef(node_name="初审", node_order=1, owner_role="matter_owner", sla_hours=24),
            NodeDef(node_name="复审", node_order=2, owner_role="dept_leader", sla_hours=48),
            NodeDef(node_name="终审", node_order=3, owner_role="admin", sla_hours=72),
        ]

        wf_service = WorkflowService()
        template = await wf_service.create_template(
            db_session,
            TemplateCreate(name="招生审批流程", matter_type_id=1, nodes=nodes),
        )
        assert template.name == "招生审批流程"
        assert template.is_active is True
