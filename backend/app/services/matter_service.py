from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.matter import (
    Matter,
    MatterMember,
    MatterComment,
)
from app.models.document import MatterType, Document, DocumentVersion
from app.models.workflow import (
    WorkflowTemplate,
    WorkflowTemplateNode,
    WorkflowNode,
)
from app.core.pagination import PaginationParams
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
    ConflictException,
)


class MatterService:

    async def create_matter(
        self, db: AsyncSession, data: "MatterCreate", user_id: int
    ) -> Matter:
        matter_type_result = await db.execute(
            select(MatterType).where(MatterType.id == data.type_id)
        )
        matter_type = matter_type_result.scalars().first()
        if not matter_type:
            raise NotFoundException(resource="MatterType")

        matter_no = await self._generate_matter_no(db)

        matter = Matter(
            matter_no=matter_no,
            title=data.title,
            type_id=data.type_id,
            owner_id=user_id,
            status="pending",
            is_key_project=data.is_key_project if hasattr(data, "is_key_project") else False,
            due_date=data.due_date,
            description=data.description,
        )
        db.add(matter)
        await db.flush()

        owner_member = MatterMember(
            matter_id=matter.id,
            user_id=user_id,
            role_in_matter="owner",
        )
        db.add(owner_member)

        if hasattr(data, "member_ids") and data.member_ids:
            for member_id in data.member_ids:
                if member_id == user_id:
                    continue
                member = MatterMember(
                    matter_id=matter.id,
                    user_id=member_id,
                    role_in_matter="collaborator",
                )
                db.add(member)

        if hasattr(data, "workflow_template_id") and data.workflow_template_id:
            from app.services.workflow_service import workflow_service
            await workflow_service.instantiate_nodes(
                db, matter.id, data.workflow_template_id
            )

        await db.commit()
        await db.refresh(matter)
        return matter

    async def get_matter(
        self,
        db: AsyncSession,
        matter_id: int,
        current_user: dict,
    ) -> Matter:
        stmt = (
            select(Matter)
            .options(
                selectinload(Matter.owner),
                selectinload(Matter.matter_type_obj),
                selectinload(Matter.members).selectinload(MatterMember.user),
                selectinload(Matter.nodes),
                selectinload(Matter.current_node),
                selectinload(Matter.comments),
            )
            .where(Matter.id == matter_id)
        )
        result = await db.execute(stmt)
        matter = result.scalars().first()

        if not matter:
            raise NotFoundException(resource="Matter")

        await self._check_matter_access(db, matter, current_user)
        return matter

    async def get_matters(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        filters: dict,
        current_user: dict,
    ) -> tuple[list[Matter], int]:
        conditions = []
        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])

        if "admin" not in user_roles and "dept_leader" not in user_roles:
            conditions.append(
                Matter.id.in_(
                    select(MatterMember.matter_id).where(
                        MatterMember.user_id == user_id
                    )
                )
            )

        if filters.get("type_id"):
            conditions.append(Matter.type_id == filters["type_id"])
        if filters.get("status"):
            conditions.append(Matter.status == filters["status"])
        if filters.get("owner_id"):
            conditions.append(Matter.owner_id == filters["owner_id"])
        if filters.get("is_key_project") is not None:
            conditions.append(Matter.is_key_project == filters["is_key_project"])
        if filters.get("keyword"):
            kw = f"%{filters['keyword']}%"
            conditions.append(
                or_(
                    Matter.title.ilike(kw),
                    Matter.matter_no.ilike(kw),
                    Matter.description.ilike(kw),
                )
            )

        base_query = (
            select(Matter)
            .options(
                selectinload(Matter.owner),
                selectinload(Matter.matter_type_obj),
                selectinload(Matter.current_node),
            )
            .where(and_(*conditions) if conditions else True)
        )

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(Matter.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def update_matter(
        self,
        db: AsyncSession,
        matter_id: int,
        data: "MatterUpdate",
        current_user: dict,
    ) -> Matter:
        matter = await self.get_matter(db, matter_id, current_user)

        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])
        if matter.owner_id != user_id and "admin" not in user_roles:
            raise ForbiddenException(
                detail="Only the matter owner or admin can update this matter"
            )

        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if hasattr(matter, key) and key not in ("id", "matter_no"):
                setattr(matter, key, value)

        await db.commit()
        await db.refresh(matter)
        return matter

    async def update_status(
        self,
        db: AsyncSession,
        matter_id: int,
        data: "MatterStatusUpdate",
        current_user: dict,
    ) -> Matter:
        matter = await self.get_matter(db, matter_id, current_user)

        valid_transitions = {
            "pending": ["in_progress", "cancelled"],
            "in_progress": ["paused", "completed", "cancelled"],
            "paused": ["in_progress", "cancelled"],
            "completed": [],
            "cancelled": [],
        }

        current_status = matter.status
        new_status = data.status

        if new_status == current_status:
            return matter

        allowed = valid_transitions.get(current_status, [])
        if new_status not in allowed:
            raise ValidationException(
                detail=f"Cannot transition from '{current_status}' to '{new_status}'. "
                       f"Allowed transitions: {allowed}"
            )

        matter.status = new_status
        matter.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(matter)
        return matter

    async def delete_matter(
        self,
        db: AsyncSession,
        matter_id: int,
        current_user: dict,
    ) -> bool:
        matter = await self.get_matter(db, matter_id, current_user)

        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])
        if matter.owner_id != user_id and "admin" not in user_roles:
            raise ForbiddenException(
                detail="Only the matter owner or admin can delete this matter"
            )

        matter.status = "cancelled"
        await db.commit()
        return True

    async def add_members(
        self,
        db: AsyncSession,
        matter_id: int,
        data: "MatterMemberAdd",
        current_user: dict,
    ) -> list[MatterMember]:
        matter = await self.get_matter(db, matter_id, current_user)

        new_members = []
        for user_id in data.user_ids:
            existing = await db.execute(
                select(MatterMember).where(
                    MatterMember.matter_id == matter_id,
                    MatterMember.user_id == user_id,
                )
            )
            if existing.scalars().first():
                continue

            member = MatterMember(
                matter_id=matter_id,
                user_id=user_id,
                role_in_matter=data.role_in_matter if hasattr(data, "role_in_matter") else "collaborator",
            )
            db.add(member)
            new_members.append(member)

        await db.commit()
        for member in new_members:
            await db.refresh(member)
        return new_members

    async def remove_member(
        self,
        db: AsyncSession,
        matter_id: int,
        user_id: int,
        current_user: dict,
    ) -> bool:
        matter = await self.get_matter(db, matter_id, current_user)

        if matter.owner_id == user_id:
            raise ValidationException(
                detail="Cannot remove the matter owner from members"
            )

        member_result = await db.execute(
            select(MatterMember).where(
                MatterMember.matter_id == matter_id,
                MatterMember.user_id == user_id,
            )
        )
        member = member_result.scalars().first()
        if not member:
            raise NotFoundException(resource="MatterMember")

        await db.delete(member)
        await db.commit()
        return True

    async def get_members(
        self, db: AsyncSession, matter_id: int
    ) -> list[MatterMember]:
        stmt = (
            select(MatterMember)
            .options(selectinload(MatterMember.user))
            .where(MatterMember.matter_id == matter_id)
            .order_by(MatterMember.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_matter_documents(
        self, db: AsyncSession, matter_id: int
    ) -> list[Document]:
        stmt = (
            select(Document)
            .options(
                selectinload(Document.owner),
                selectinload(Document.current_version),
            )
            .where(
                Document.matter_id == matter_id,
                Document.is_deleted == False,
            )
            .order_by(Document.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def batch_assign(
        self, db: AsyncSession, matter_ids: list[int], assignee_id: int
    ) -> int:
        """Batch reassign matters to a new owner. Returns count of updated matters."""
        result = await db.execute(
            select(Matter).where(Matter.id.in_(matter_ids))
        )
        matters = result.scalars().all()
        for m in matters:
            m.owner_id = assignee_id
        await db.commit()
        return len(matters)

    async def calculate_progress(
        self, db: AsyncSession, matter_id: int
    ) -> float:
        total_result = await db.execute(
            select(func.count()).where(WorkflowNode.matter_id == matter_id)
        )
        total = total_result.scalar() or 0

        if total == 0:
            return 0.0

        completed_result = await db.execute(
            select(func.count()).where(
                WorkflowNode.matter_id == matter_id,
                WorkflowNode.status.in_(["completed", "skipped"]),
            )
        )
        completed = completed_result.scalar() or 0

        progress = round((completed / total) * 100, 2)

        await db.execute(
            update(Matter)
            .where(Matter.id == matter_id)
            .values(progress=progress)
        )
        await db.commit()

        return progress

    async def _generate_matter_no(self, db: AsyncSession) -> str:
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"MT-{today_str}-"

        max_no_result = await db.execute(
            select(func.max(Matter.matter_no)).where(
                Matter.matter_no.like(f"{prefix}%")
            )
        )
        max_no = max_no_result.scalar()

        if max_no:
            try:
                last_seq = int(max_no.split("-")[-1])
                seq = last_seq + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

        return f"{prefix}{seq:04d}"

    async def _check_matter_access(
        self, db: AsyncSession, matter: Matter, current_user: dict
    ) -> None:
        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])

        if "admin" in user_roles or "dept_leader" in user_roles:
            return

        if matter.owner_id == user_id:
            return

        member_result = await db.execute(
            select(MatterMember).where(
                MatterMember.matter_id == matter.id,
                MatterMember.user_id == user_id,
            )
        )
        if not member_result.scalars().first():
            raise ForbiddenException(
                detail="You do not have access to this matter"
            )


class MatterCommentService:

    async def get_comments(
        self,
        db: AsyncSession,
        matter_id: int,
        pagination: PaginationParams,
    ) -> tuple[list[MatterComment], int]:
        base_query = (
            select(MatterComment)
            .options(selectinload(MatterComment.user))
            .where(MatterComment.matter_id == matter_id)
        )

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(MatterComment.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def add_comment(
        self,
        db: AsyncSession,
        matter_id: int,
        user_id: int,
        content: str,
    ) -> MatterComment:
        matter_result = await db.execute(
            select(Matter).where(Matter.id == matter_id)
        )
        matter = matter_result.scalars().first()
        if not matter:
            raise NotFoundException(resource="Matter")

        if not content or not content.strip():
            raise ValidationException(detail="Comment content cannot be empty")

        comment = MatterComment(
            matter_id=matter_id,
            user_id=user_id,
            content=content.strip(),
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment


matter_service = MatterService()
matter_comment_service = MatterCommentService()
