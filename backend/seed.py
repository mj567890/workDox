"""Seed initial data for ODMS development/testing."""
import sys
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.core.security import hash_password
from app.models.base import Base
from app.models.department import Department
from app.models.user import User, user_role
from app.models.role import Role
from app.models.document import MatterType, DocumentCategory, Tag
from app.models.matter import Matter, MatterMember
from app.models.workflow import WorkflowTemplate, WorkflowTemplateNode
from app.models.task import Task, Notification

settings = get_settings()
engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)


def seed():
    with Session(engine) as db:
        # Check if already seeded
        existing = db.execute(select(Role).limit(1)).scalar_one_or_none()
        if existing:
            print("Database already seeded. Skipping.")
            return

        # ── Roles ──
        roles = [
            Role(role_name="普通员工", role_code="general_staff", description="基本用户角色"),
            Role(role_name="事项负责人", role_code="matter_owner", description="业务事项负责人"),
            Role(role_name="部门领导", role_code="dept_leader", description="部门领导"),
            Role(role_name="系统管理员", role_code="admin", description="系统管理员"),
        ]
        db.add_all(roles)
        db.flush()

        # ── Department ──
        dept = Department(name="综合办公室", code="office")
        db.add(dept)
        db.flush()

        # ── Users ──
        admin_user = User(
            username="admin",
            password_hash=hash_password("admin123"),
            real_name="系统管理员",
            email="admin@odms.local",
            department_id=dept.id,
            status="active",
        )
        staff_user = User(
            username="zhangsan",
            password_hash=hash_password("zhangsan123"),
            real_name="张三",
            email="zhangsan@odms.local",
            department_id=dept.id,
            status="active",
        )
        leader_user = User(
            username="lisi",
            password_hash=hash_password("lisi123"),
            real_name="李四",
            email="lisi@odms.local",
            department_id=dept.id,
            status="active",
        )
        db.add_all([admin_user, staff_user, leader_user])
        db.flush()

        # Assign roles: admin -> admin, zhangsan -> matter_owner + general_staff, lisi -> dept_leader + general_staff
        db.execute(
            user_role.insert().values([
                {"user_id": admin_user.id, "role_id": roles[3].id},
                {"user_id": staff_user.id, "role_id": roles[0].id},
                {"user_id": staff_user.id, "role_id": roles[1].id},
                {"user_id": leader_user.id, "role_id": roles[0].id},
                {"user_id": leader_user.id, "role_id": roles[2].id},
            ])
        )

        # ── Matter Types ──
        matter_types = [
            MatterType(name="常规行政事项", code="general_admin", description="日常行政办公事项"),
            MatterType(name="项目审批事项", code="project_approval", description="需要多级审批的项目类事项"),
            MatterType(name="会议纪要事项", code="meeting_minutes", description="会议相关事项"),
            MatterType(name="文件签发事项", code="doc_issuance", description="公文签发流转事项"),
        ]
        db.add_all(matter_types)
        db.flush()

        # ── Document Categories ──
        doc_categories = [
            DocumentCategory(name="通知文件", code="notice", sort_order=1, is_system=True),
            DocumentCategory(name="方案材料", code="plan_material", sort_order=2, is_system=True),
            DocumentCategory(name="报审材料", code="approval_material", sort_order=3, is_system=True),
            DocumentCategory(name="签批文件", code="signed_doc", sort_order=4, is_system=True),
            DocumentCategory(name="会议纪要", code="meeting_notes", sort_order=5, is_system=True),
            DocumentCategory(name="其他材料", code="other", sort_order=99, is_system=True),
        ]
        db.add_all(doc_categories)
        db.flush()

        # ── Tags ──
        tags = [
            Tag(name="紧急", color="#F56C6C"),
            Tag(name="重要", color="#E6A23C"),
            Tag(name="已签批", color="#67C23A"),
            Tag(name="待审核", color="#409EFF"),
            Tag(name="机密", color="#909399"),
        ]
        db.add_all(tags)
        db.flush()

        # ── Sample Matter ──
        matter = Matter(
            matter_no="ODMS-2026-0001",
            title="2026年度信息化建设方案审批",
            type_id=matter_types[1].id,
            owner_id=staff_user.id,
            status="in_progress",
            is_key_project=True,
            progress=35.0,
            due_date=None,
            description="审批学院2026年度信息化建设方案，涉及采购预算、技术选型等内容。",
        )
        db.add(matter)
        db.flush()

        # Matter members
        db.add_all([
            MatterMember(matter_id=matter.id, user_id=staff_user.id, role_in_matter="owner"),
            MatterMember(matter_id=matter.id, user_id=leader_user.id, role_in_matter="collaborator"),
        ])

        # ── Workflow Template ──
        template = WorkflowTemplate(
            name="标准审批流程",
            matter_type_id=matter_types[1].id,
            is_active=True,
            description="适用于项目审批类事项",
        )
        db.add(template)
        db.flush()

        db.add_all([
            WorkflowTemplateNode(template_id=template.id, node_name="材料准备", node_order=1, owner_role="matter_owner", description="准备审批所需材料"),
            WorkflowTemplateNode(template_id=template.id, node_name="部门审核", node_order=2, owner_role="dept_leader", description="部门领导审核"),
            WorkflowTemplateNode(template_id=template.id, node_name="终审确认", node_order=3, owner_role="dept_leader", description="终审签字确认"),
            WorkflowTemplateNode(template_id=template.id, node_name="归档", node_order=4, owner_role="general_staff", description="归档材料"),
        ])

        # ── Sample Task ──
        task = Task(
            title="审核信息化建设方案",
            matter_id=matter.id,
            assignee_id=leader_user.id,
            assigner_id=staff_user.id,
            status="pending",
            priority="high",
        )
        db.add(task)

        # ── Sample Notification ──
        notif = Notification(
            user_id=leader_user.id,
            type="task_assigned",
            title="新任务待办",
            content="张三给您分配了任务：审核信息化建设方案",
            related_matter_id=matter.id,
        )
        db.add(notif)

        db.commit()
        print("Seed data created successfully!")
        print()
        print("Test accounts:")
        print("  admin    / admin123     (系统管理员)")
        print("  zhangsan / zhangsan123  (事项负责人)")
        print("  lisi     / lisi123      (部门领导)")


if __name__ == "__main__":
    seed()
