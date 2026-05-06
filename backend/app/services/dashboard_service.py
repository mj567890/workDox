"""Dashboard service — uses ProjectTask / TaskTemplate / ProjectStage (no Matter dependency)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task_manager import (
    TaskTemplate, ProjectTask, ProjectStage, ProjectSlot,
)
from app.models.document import Document


class DashboardService:

    # ── Overview ──────────────────────────────────────────────────

    async def get_overview(self, db: AsyncSession) -> dict:
        now = datetime.now(timezone.utc)

        total_tasks = (await db.execute(select(func.count(ProjectTask.id)))).scalar() or 0
        active_tasks = (await db.execute(
            select(func.count(ProjectTask.id)).where(ProjectTask.status == "in_progress")
        )).scalar() or 0
        completed_tasks = (await db.execute(
            select(func.count(ProjectTask.id)).where(ProjectTask.status == "completed")
        )).scalar() or 0

        completion_rate = (completed_tasks / total_tasks) if total_tasks > 0 else 0.0

        # pipeline_progress — proportion of stages in active/in_progress state
        total_stages = (await db.execute(select(func.count(ProjectStage.id)))).scalar() or 0
        completed_stages = (await db.execute(
            select(func.count(ProjectStage.id)).where(ProjectStage.status == "completed")
        )).scalar() or 0
        pipeline_progress = (completed_stages / total_stages) if total_stages > 0 else 0.0

        # overdue stages — stages whose task is not "completed" and stage status is not "completed"
        overdue_stages = (await db.execute(
            select(func.count(ProjectStage.id))
            .join(ProjectTask, ProjectStage.task_id == ProjectTask.id)
            .where(
                and_(
                    ProjectTask.status != "completed",
                    ProjectStage.status.in_(["active", "overdue"]),
                )
            )
        )).scalar() or 0

        total_slots = (await db.execute(select(func.count(ProjectSlot.id)))).scalar() or 0
        filled_slots = (await db.execute(
            select(func.count(ProjectSlot.id)).where(ProjectSlot.status == "completed")
        )).scalar() or 0

        total_documents = (await db.execute(
            select(func.count(Document.id))
        )).scalar() or 0

        return {
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": round(completion_rate, 4),
            "pipeline_progress": round(pipeline_progress, 4),
            "overdue_stages": overdue_stages,
            "total_slots": total_slots,
            "filled_slots": filled_slots,
            "total_documents": total_documents,
        }

    # ── Key Projects (active tasks) ──────────────────────────────

    async def get_active_tasks(self, db: AsyncSession) -> list[dict]:
        stmt = (
            select(ProjectTask)
            .options(selectinload(ProjectTask.template))
            .where(ProjectTask.status.in_(["pending", "in_progress"]))
            .order_by(ProjectTask.created_at.desc())
            .limit(20)
        )
        result = await db.execute(stmt)
        tasks = result.scalars().all()

        return [
            {
                "task_id": t.id,
                "title": t.title,
                "template_name": t.template.name if t.template else "",
                "current_stage": self._current_stage_name(t),
                "current_stage_order": t.current_stage_order or 1,
                "progress": self._calc_progress(t),
                "status": t.status or "pending",
                "creator_id": t.creator_id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]

    # ── Risk Alerts ──────────────────────────────────────────────

    async def get_risk_alerts(self, db: AsyncSession) -> list[dict]:
        stmt = (
            select(ProjectStage)
            .options(
                selectinload(ProjectStage.project_task).selectinload(ProjectTask.template)
            )
            .where(
                and_(
                    ProjectStage.status.in_(["active", "overdue"]),
                    ProjectStage.project_task.has(ProjectTask.status != "completed"),
                )
            )
            .order_by(ProjectStage.order)
            .limit(15)
        )
        result = await db.execute(stmt)
        stages = result.scalars().all()

        alerts = []
        for s in stages:
            risk_type = "overdue" if s.status == "overdue" else "stalled"
            risk_level = "high" if s.status == "overdue" else "medium"
            alerts.append({
                "task_id": s.task_id,
                "title": s.project_task.title if s.project_task else "",
                "risk_type": risk_type,
                "risk_level": risk_level,
                "description": f"阶段「{s.name}」状态异常：{s.status}",
                "stage_name": s.name,
            })
        return alerts

    # ── Charts ───────────────────────────────────────────────────

    async def get_stage_funnel(self, db: AsyncSession) -> list[dict]:
        stmt = (
            select(ProjectStage.order, func.count(ProjectStage.id))
            .group_by(ProjectStage.order)
            .order_by(ProjectStage.order)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [{"stage_order": row[0] or 0, "count": row[1]} for row in rows]

    async def get_monthly_trend(self, db: AsyncSession) -> list[dict]:
        # Last 6 months trend
        months = []
        now = datetime.now(timezone.utc)
        for i in range(5, -1, -1):
            d = now.replace(day=1) - timedelta(days=1)
            d = d.replace(day=1)
            if i < 5:
                d = now.replace(day=1) - timedelta(days=i * 30)
                d = d.replace(day=1)
            else:
                # First month in range
                d = now.replace(day=1) - timedelta(days=5 * 30)
                d = d.replace(day=1)
            month_start = d
            if d.month == 12:
                month_end = d.replace(year=d.year + 1, month=1, day=1)
            else:
                month_end = d.replace(month=d.month + 1, day=1)
            month_label = d.strftime("%Y-%m")

            total = (await db.execute(
                select(func.count(ProjectTask.id)).where(
                    and_(
                        ProjectTask.created_at >= month_start,
                        ProjectTask.created_at < month_end,
                    )
                )
            )).scalar() or 0
            completed = (await db.execute(
                select(func.count(ProjectTask.id)).where(
                    and_(
                        ProjectTask.status == "completed",
                        ProjectTask.updated_at >= month_start,
                        ProjectTask.updated_at < month_end,
                    )
                )
            )).scalar() or 0
            months.append({"month": month_label, "total": total, "completed": completed})
        return months

    async def get_template_distribution(self, db: AsyncSession) -> list[dict]:
        stmt = (
            select(TaskTemplate.name, func.count(ProjectTask.id))
            .outerjoin(ProjectTask, ProjectTask.template_id == TaskTemplate.id)
            .group_by(TaskTemplate.name)
            .order_by(func.count(ProjectTask.id).desc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [{"name": row[0] or "未分类", "count": row[1]} for row in rows]

    async def get_status_distribution(self, db: AsyncSession) -> list[dict]:
        status_labels = {
            "pending": "待开始",
            "in_progress": "进行中",
            "completed": "已完成",
            "cancelled": "已取消",
        }
        stmt = (
            select(ProjectTask.status, func.count(ProjectTask.id))
            .group_by(ProjectTask.status)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {"status": row[0] or "unknown", "label": status_labels.get(row[0], row[0] or "未知"), "count": row[1]}
            for row in rows
        ]

    async def get_department_workload(self, db: AsyncSession) -> list[dict]:
        from app.models.user import User
        from app.models.department import Department

        stmt = (
            select(
                Department.name,
                func.count(ProjectTask.id).label("total"),
                func.count(func.nullif(ProjectTask.status == "completed", False)).label("completed_tasks"),
            )
            .select_from(Department)
            .outerjoin(User, User.department_id == Department.id)
            .outerjoin(ProjectTask, ProjectTask.creator_id == User.id)
            .group_by(Department.name)
            .order_by(func.count(ProjectTask.id).desc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {"department_name": row[0] or "未分配", "total_tasks": row[1] or 0, "completed_tasks": row[2] or 0}
            for row in rows
        ]

    # ── Personal Stats ───────────────────────────────────────────

    async def get_personal_stats(self, db: AsyncSession, user_id: int) -> dict:
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        total_tasks = (await db.execute(
            select(func.count(ProjectTask.id)).where(ProjectTask.creator_id == user_id)
        )).scalar() or 0

        week_total = (await db.execute(
            select(func.count(ProjectTask.id)).where(
                and_(
                    ProjectTask.creator_id == user_id,
                    ProjectTask.updated_at >= week_start,
                )
            )
        )).scalar() or 0

        week_completed = (await db.execute(
            select(func.count(ProjectTask.id)).where(
                and_(
                    ProjectTask.creator_id == user_id,
                    ProjectTask.status == "completed",
                    ProjectTask.updated_at >= week_start,
                )
            )
        )).scalar() or 0

        overdue_rate = 0.0  # simplified
        avg_completion_days = 0.0  # simplified
        streak_days = 0  # simplified

        status_dist = await self._get_user_status_distribution(db, user_id)

        return {
            "week_completed_tasks": week_completed,
            "week_total_tasks": week_total,
            "overdue_rate": overdue_rate,
            "avg_completion_days": avg_completion_days,
            "streak_days": streak_days,
            "total_tasks": total_tasks,
            "status_distribution": status_dist,
        }

    async def _get_user_status_distribution(self, db: AsyncSession, user_id: int) -> list[dict]:
        status_labels = {
            "pending": "待开始",
            "in_progress": "进行中",
            "completed": "已完成",
            "cancelled": "已取消",
        }
        stmt = (
            select(ProjectTask.status, func.count(ProjectTask.id))
            .where(ProjectTask.creator_id == user_id)
            .group_by(ProjectTask.status)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {"status": row[0] or "unknown", "label": status_labels.get(row[0], row[0] or "未知"), "count": row[1]}
            for row in rows
        ]

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _current_stage_name(task: ProjectTask) -> str:
        if task.stages:
            for s in task.stages:
                if s.order == task.current_stage_order:
                    return s.name
            # Fallback: return the last stage name
            return task.stages[-1].name if task.stages else ""
        return ""

    @staticmethod
    def _calc_progress(task: ProjectTask) -> float:
        if not task.stages:
            return 0.0
        completed = sum(1 for s in task.stages if s.status == "completed")
        return round(completed / len(task.stages) * 100, 1)
