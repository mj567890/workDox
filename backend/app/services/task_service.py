from datetime import datetime, timezone

from sqlalchemy import select, func, and_, or_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, Notification
from app.models.matter import Matter, MatterMember
from app.core.pagination import PaginationParams
from app.core.exceptions import NotFoundException, ValidationException


class TaskService:

    async def create_task(
        self, db: AsyncSession, data: "TaskCreate", assigner_id: int
    ) -> Task:
        matter_result = await db.execute(
            select(Matter).where(Matter.id == data.matter_id)
        )
        matter = matter_result.scalars().first()
        if not matter:
            raise NotFoundException(resource="Matter")

        if data.due_time and data.due_time < datetime.now(timezone.utc):
            raise ValidationException(detail="Due time must be in the future")

        task = Task(
            matter_id=data.matter_id,
            node_id=data.node_id,
            title=data.title,
            assigner_id=assigner_id,
            assignee_id=data.assignee_id,
            status="pending",
            priority=data.priority if hasattr(data, "priority") else "normal",
            due_time=data.due_time,
            description=data.description,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        await self._create_assignment_notification(
            db, task, assigner_id
        )

        return task

    async def get_tasks(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        filters: dict,
        current_user: dict,
    ) -> tuple[list[Task], int]:
        conditions = []
        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])

        if "admin" not in user_roles and "dept_leader" not in user_roles:
            accessible_matter_ids = current_user.get("accessible_matter_ids", [])
            if accessible_matter_ids:
                conditions.append(or_(
                    Task.assignee_id == user_id,
                    Task.assigner_id == user_id,
                    Task.matter_id.in_(accessible_matter_ids),
                ))
            else:
                conditions.append(Task.assignee_id == user_id)

        if filters.get("status"):
            conditions.append(Task.status == filters["status"])
        if filters.get("priority"):
            conditions.append(Task.priority == filters["priority"])
        if filters.get("matter_id"):
            conditions.append(Task.matter_id == filters["matter_id"])
        if filters.get("assignee_id") and "admin" in user_roles:
            conditions.append(Task.assignee_id == filters["assignee_id"])
        if filters.get("keyword"):
            conditions.append(Task.title.ilike(f"%{filters['keyword']}%"))

        base_query = select(Task).options(
            selectinload(Task.matter),
            selectinload(Task.assigner),
            selectinload(Task.assignee),
            selectinload(Task.node),
        )
        if conditions:
            base_query = base_query.where(and_(*conditions))

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(Task.due_time.asc().nulls_last(), Task.priority.desc(), Task.id.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def get_task(self, db: AsyncSession, task_id: int) -> Task:
        stmt = (
            select(Task)
            .options(
                selectinload(Task.matter),
                selectinload(Task.assigner),
                selectinload(Task.assignee),
                selectinload(Task.node),
            )
            .where(Task.id == task_id)
        )
        result = await db.execute(stmt)
        task = result.scalars().first()
        if not task:
            raise NotFoundException(resource="Task")
        return task

    async def update_task(
        self,
        db: AsyncSession,
        task_id: int,
        data: "TaskUpdate",
        current_user: dict,
    ) -> Task:
        task = await self.get_task(db, task_id)

        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("status") == "completed":
            update_data.setdefault("due_time", task.due_time)
            if "actual_finish_time" not in update_data:
                update_data["actual_finish_time"] = datetime.now(timezone.utc)

        for key, value in update_data.items():
            if hasattr(task, key) and key != "id":
                setattr(task, key, value)

        await db.commit()
        await db.refresh(task)
        return task

    async def delete_task(self, db: AsyncSession, task_id: int) -> bool:
        task = await self.get_task(db, task_id)
        await db.delete(task)
        await db.commit()
        return True

    async def batch_complete_tasks(
        self, db: AsyncSession, task_ids: list[int]
    ) -> int:
        """Batch complete tasks by IDs. Returns count of updated tasks."""
        result = await db.execute(
            select(Task).where(Task.id.in_(task_ids))
        )
        tasks = result.scalars().all()
        for task in tasks:
            task.status = "completed"
        await db.commit()
        return len(tasks)

    async def get_tasks_for_export(
        self, db: AsyncSession, current_user: dict
    ) -> list[Task]:
        """Get tasks for Excel export, respecting access control (max 10000)."""
        conditions = []
        user_id = current_user.get("id")
        user_roles = current_user.get("roles", [])

        if "admin" not in user_roles and "dept_leader" not in user_roles:
            accessible_matter_ids = current_user.get("accessible_matter_ids", [])
            if accessible_matter_ids:
                conditions.append(or_(
                    Task.assignee_id == user_id,
                    Task.assigner_id == user_id,
                    Task.matter_id.in_(accessible_matter_ids),
                ))
            else:
                conditions.append(Task.assignee_id == user_id)

        query = select(Task).options(
            selectinload(Task.matter),
            selectinload(Task.assignee),
            selectinload(Task.assigner),
        )
        if conditions:
            query = query.where(and_(*conditions))

        result = await db.execute(
            query.order_by(Task.created_at.desc()).limit(10000)
        )
        return list(result.scalars().all())

    async def _create_assignment_notification(
        self, db: AsyncSession, task: Task, assigner_id: int
    ) -> None:
        notification = Notification(
            user_id=task.assignee_id,
            type="task_assigned",
            title=f"New task assigned: {task.title}",
            content=f"You have been assigned a new task: {task.title}",
            related_matter_id=task.matter_id,
        )
        db.add(notification)
        await db.commit()
