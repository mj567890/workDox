from typing import Optional, Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.matter import Matter
from app.models.document import Document
from app.models.task import Task
from app.models.workflow import WorkflowNode


class DashboardService:

    def _matter_filter(self, matter_ids: Optional[Sequence[int]]):
        """Return a WHERE clause for matter_ids.

        None  = no filter (admin sees all)
        []   = user has access to zero matters -> use impossible condition
        [...] = filter to these IDs
        """
        if matter_ids is None:
            return True
        if not matter_ids:
            return False
        return Matter.id.in_(matter_ids)

    # ------------------------------------------------------------------
    async def get_overview(
        self, db: AsyncSession, matter_ids: Optional[Sequence[int]] = None
    ) -> dict:
        mf = self._matter_filter(matter_ids)

        total_matters = (
            await db.execute(select(func.count(Matter.id)).where(mf))
        ).scalar() or 0

        in_progress = (
            await db.execute(
                select(func.count(Matter.id)).where(
                    and_(Matter.status == "in_progress", mf)
                )
            )
        ).scalar() or 0

        completed = (
            await db.execute(
                select(func.count(Matter.id)).where(
                    and_(Matter.status == "completed", mf)
                )
            )
        ).scalar() or 0

        now = datetime.now(timezone.utc)
        overdue = (
            await db.execute(
                select(func.count(Matter.id)).where(
                    and_(
                        Matter.status.in_(["pending", "in_progress"]),
                        Matter.due_date < now,
                        mf,
                    )
                )
            )
        ).scalar() or 0

        completion_rate = round(
            completed / total_matters if total_matters > 0 else 0.0, 2
        )

        total_documents = (
            await db.execute(
                select(func.count(Document.id)).where(
                    and_(Document.is_deleted == False, mf if mf is not True else True)
                )
            )
        ).scalar() or 0

        # near-deadline (within 3 days)
        near_deadline = (
            await db.execute(
                select(func.count(Matter.id)).where(
                    and_(
                        Matter.status.in_(["pending", "in_progress"]),
                        Matter.due_date.between(
                            now, now + timedelta(days=3)
                        ),
                        mf,
                    )
                )
            )
        ).scalar() or 0

        risk_count = overdue + near_deadline

        return {
            "total_matters": total_matters,
            "total_documents": total_documents,
            "pending_tasks": 0,  # caller fills in per-user task count
            "completed_matters": completed,
            "in_progress_matters": in_progress,
            "overdue_matters": overdue,
            "completion_rate": completion_rate,
            "risk_count": risk_count,
        }

    # ------------------------------------------------------------------
    async def get_key_projects(
        self, db: AsyncSession, matter_ids: Optional[Sequence[int]] = None
    ) -> list[dict]:
        mf = self._matter_filter(matter_ids)
        result = await db.execute(
            select(Matter)
            .options(selectinload(Matter.owner))
            .where(mf)
            .order_by(Matter.progress.asc(), Matter.due_date.asc())
            .limit(20)
        )
        matters = result.scalars().all()

        now = datetime.now(timezone.utc)
        projects = []
        for m in matters:
            risk_level = "low"
            if m.due_date and m.due_date < now and m.status not in (
                "completed",
                "cancelled",
            ):
                risk_level = "high"
            elif (
                m.due_date
                and m.due_date < now + timedelta(days=3)
                and m.status not in ("completed", "cancelled")
            ):
                risk_level = "medium"

            current_node_name = None
            if m.current_node_id:
                node_result = await db.execute(
                    select(WorkflowNode.node_name).where(
                        WorkflowNode.id == m.current_node_id
                    )
                )
                current_node_name = node_result.scalar_one_or_none()

            projects.append(
                {
                    "matter_id": m.id,
                    "matter_no": m.matter_no,
                    "title": m.title,
                    "progress": m.progress,
                    "status": m.status,
                    "current_node": current_node_name,
                    "owner_name": m.owner.real_name if m.owner else None,
                    "due_date": m.due_date.isoformat() if m.due_date else None,
                    "risk_level": risk_level,
                }
            )
        return projects

    # ------------------------------------------------------------------
    async def get_risk_alerts(
        self, db: AsyncSession, matter_ids: Optional[Sequence[int]] = None
    ) -> list[dict]:
        mf = self._matter_filter(matter_ids)
        now = datetime.now(timezone.utc)
        near_deadline = now + timedelta(days=3)
        alerts = []

        # Overdue
        overdue_result = await db.execute(
            select(Matter).options(selectinload(Matter.owner)).where(
                and_(
                    Matter.status.in_(["pending", "in_progress"]),
                    Matter.due_date < now,
                    mf,
                )
            ).order_by(Matter.due_date)
        )
        for m in overdue_result.scalars().all():
            days_overdue = 0
            if m.due_date:
                days_overdue = max((now - m.due_date).days, 0)
            risk_level = "high" if days_overdue > 7 else "medium"
            alerts.append(
                {
                    "matter_id": m.id,
                    "matter_no": m.matter_no,
                    "title": m.title,
                    "risk_type": "overdue",
                    "risk_level": risk_level,
                    "description": f"已逾期 {days_overdue} 天"
                    if days_overdue > 0
                    else "即将逾期",
                    "days_overdue": days_overdue if days_overdue > 0 else None,
                }
            )

        # Near deadline
        near_result = await db.execute(
            select(Matter).options(selectinload(Matter.owner)).where(
                and_(
                    Matter.status.in_(["pending", "in_progress"]),
                    Matter.due_date >= now,
                    Matter.due_date <= near_deadline,
                    mf,
                )
            ).order_by(Matter.due_date)
        )
        for m in near_result.scalars().all():
            days_remaining = 0
            if m.due_date:
                days_remaining = (m.due_date - now).days
            risk_level = "high" if days_remaining <= 1 else "medium"
            alerts.append(
                {
                    "matter_id": m.id,
                    "matter_no": m.matter_no,
                    "title": m.title,
                    "risk_type": "near_deadline",
                    "risk_level": risk_level,
                    "description": f"距截止日期仅剩 {days_remaining} 天",
                    "days_overdue": None,
                }
            )

        return alerts

    # ------------------------------------------------------------------
    async def get_progress_chart(
        self, db: AsyncSession, matter_ids: Optional[Sequence[int]] = None
    ) -> dict:
        mf = self._matter_filter(matter_ids)
        now = datetime.now(timezone.utc)

        labels = []
        completed = []
        in_progress = []
        pending = []

        for i in range(5, -1, -1):
            period_start = now.replace(
                year=now.year, month=now.month, day=1
            ) - timedelta(days=i * 30)
            period_start = period_start.replace(day=1)
            period_label = period_start.strftime("%Y-%m")

            month_start = period_start
            if i == 0:
                month_end = now + timedelta(days=1)
            else:
                next_month = month_start.month + 1
                next_year = month_start.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                month_end = month_start.replace(
                    year=next_year, month=next_month, day=1
                )

            query = select(
                func.count(Matter.id).filter(Matter.status == "completed"),
                func.count(Matter.id).filter(Matter.status == "in_progress"),
                func.count(Matter.id).filter(Matter.status == "pending"),
            ).where(and_(Matter.created_at < month_end, mf))

            row = (await db.execute(query)).one()
            labels.append(period_label)
            completed.append(row[0] or 0)
            in_progress.append(row[1] or 0)
            pending.append(row[2] or 0)

        return {
            "labels": labels,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
        }

    # ------------------------------------------------------------------
    async def get_type_distribution(
        self, db: AsyncSession, matter_ids: Optional[Sequence[int]] = None
    ) -> list[dict]:
        from app.models.document import MatterType

        mf = self._matter_filter(matter_ids)
        result = await db.execute(
            select(MatterType.name, func.count(Matter.id))
            .outerjoin(Matter, and_(Matter.type_id == MatterType.id, mf))
            .group_by(MatterType.id, MatterType.name)
        )
        distribution = []
        for name, count in result.all():
            distribution.append({"name": name, "count": count or 0, "percentage": 0.0})

        total = sum(d["count"] for d in distribution) or 1
        for d in distribution:
            d["percentage"] = round(d["count"] / total * 100, 1)

        return distribution

    # ------------------------------------------------------------------
    async def get_personal_stats(
        self, db: AsyncSession, user_id: int
    ) -> dict:
        """Personal task statistics for the current user."""
        now = datetime.now(timezone.utc)

        # Week start (Monday)
        weekday = now.weekday()
        week_start = (now - timedelta(days=weekday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Week completed tasks
        week_completed = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.assignee_id == user_id,
                    Task.status == "completed",
                    Task.updated_at >= week_start,
                )
            )
        ).scalar() or 0

        # Week total tasks
        week_total = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.assignee_id == user_id,
                    Task.created_at >= week_start,
                )
            )
        ).scalar() or 0

        # Overdue rate
        overdue_count = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.assignee_id == user_id,
                    Task.status.in_(["pending", "in_progress"]),
                    Task.due_time < now,
                    Task.due_time.isnot(None),
                )
            )
        ).scalar() or 0
        pending_total = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.assignee_id == user_id,
                    Task.status.in_(["pending", "in_progress"]),
                )
            )
        ).scalar() or 1
        overdue_rate = round(overdue_count / pending_total, 2)

        # Priority distribution
        priority_result = await db.execute(
            select(Task.priority, func.count(Task.id))
            .where(
                Task.assignee_id == user_id,
                Task.status.in_(["pending", "in_progress"]),
            )
            .group_by(Task.priority)
        )
        priority_dist = [
            {"priority": row[0], "count": row[1]}
            for row in priority_result.all()
        ]

        # Streak: consecutive days (past 30) with at least one completed task
        streak = 0
        for i in range(30):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_count = (
                await db.execute(
                    select(func.count(Task.id)).where(
                        Task.assignee_id == user_id,
                        Task.status == "completed",
                        Task.updated_at >= day_start,
                        Task.updated_at < day_end,
                    )
                )
            ).scalar() or 0
            if day_count > 0:
                streak += 1
            else:
                break

        return {
            "week_completed_tasks": week_completed,
            "week_total_tasks": week_total,
            "overdue_rate": overdue_rate,
            "avg_completion_days": 0.0,  # simplified
            "streak_days": streak,
            "priority_distribution": priority_dist,
        }
