from datetime import datetime, timedelta, timezone
from collections import defaultdict

from sqlalchemy import select, func, extract, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task_manager import (
    TaskTemplate, StageTemplate,
    ProjectTask, ProjectStage, ProjectSlot,
)
from app.models.user import User
from app.models.document import Document


class DashboardService:

    # ── Overview ────────────────────────────────────────────────

    async def get_overview(self, db: AsyncSession) -> dict:
        now = datetime.now(timezone.utc)

        # All tasks with stages+slots loaded
        result = await db.execute(
            select(ProjectTask).options(
                selectinload(ProjectTask.stages).selectinload(ProjectStage.slots),
                selectinload(ProjectTask.template).selectinload(TaskTemplate.stages),
            )
        )
        tasks = result.scalars().all()

        total = len(tasks)
        active_tasks = [t for t in tasks if t.status in ('pending', 'active')]
        completed = sum(1 for t in tasks if t.status == 'completed')
        active_count = len(active_tasks)
        completion_rate = round(completed / total * 100, 1) if total else 0.0

        # Pipeline progress: required slots filled+waived / total required across active tasks
        total_required = 0
        filled_required = 0
        for t in active_tasks:
            for stage in t.stages:
                for slot in stage.slots:
                    if slot.is_required:
                        total_required += 1
                        if slot.status in ('filled', 'waived'):
                            filled_required += 1
        pipeline_progress = round(filled_required / total_required * 100, 1) if total_required else 0.0

        # Overdue stages: active tasks where current stage has deadline_offset_days expired
        overdue_stages = 0
        for t in active_tasks:
            current_stage = next((s for s in t.stages if s.order == t.current_stage_order), None)
            if current_stage and t.template:
                st_def = next((s for s in t.template.stages if s.order == current_stage.order), None)
                if st_def and st_def.deadline_offset_days:
                    deadline = t.created_at + timedelta(days=st_def.deadline_offset_days)
                    if deadline < now and current_stage.status != 'completed':
                        overdue_stages += 1

        # Get total documents count
        doc_result = await db.execute(select(func.count(Document.id)))
        total_documents = doc_result.scalar() or 0

        return {
            "total_tasks": total,
            "active_tasks": active_count,
            "completed_tasks": completed,
            "completion_rate": completion_rate,
            "pipeline_progress": pipeline_progress,
            "overdue_stages": overdue_stages,
            "total_slots": total_required,
            "filled_slots": filled_required,
            "total_documents": total_documents,
        }

    # ── Active Tasks ────────────────────────────────────────────

    async def get_active_tasks(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(ProjectTask).options(
                selectinload(ProjectTask.template),
                selectinload(ProjectTask.stages).selectinload(ProjectStage.slots),
            ).where(ProjectTask.status.in_(['pending', 'active']))
            .order_by(ProjectTask.created_at.desc())
        )
        tasks = result.scalars().all()

        items = []
        for t in tasks:
            current_stage = next((s for s in t.stages if s.order == t.current_stage_order), None)
            total_required = sum(1 for s in t.stages for sl in s.slots if sl.is_required)
            filled = sum(
                1 for s in t.stages for sl in s.slots
                if sl.is_required and sl.status in ('filled', 'waived')
            )
            progress = round(filled / total_required * 100, 1) if total_required else 0.0

            items.append({
                "task_id": t.id,
                "title": t.title,
                "template_name": t.template.name if t.template else "-",
                "current_stage": current_stage.name if current_stage else "-",
                "current_stage_order": t.current_stage_order,
                "progress": progress,
                "status": t.status,
                "creator_id": t.creator_id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return items

    # ── Risk Alerts ─────────────────────────────────────────────

    async def get_risk_alerts(self, db: AsyncSession) -> list[dict]:
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        result = await db.execute(
            select(ProjectTask).options(
                selectinload(ProjectTask.template).selectinload(TaskTemplate.stages),
                selectinload(ProjectTask.stages).selectinload(ProjectStage.slots),
            ).where(ProjectTask.status.in_(['pending', 'active']))
        )
        tasks = result.scalars().all()

        alerts = []
        for t in tasks:
            current_stage = next((s for s in t.stages if s.order == t.current_stage_order), None)
            if not current_stage:
                continue

            # Stalled: current stage not updated in 7+ days
            if current_stage.updated_at and current_stage.updated_at < seven_days_ago:
                days_stalled = (now - current_stage.updated_at).days
                alerts.append({
                    "task_id": t.id,
                    "title": t.title,
                    "risk_type": "停滞",
                    "risk_level": "high" if days_stalled > 14 else "medium",
                    "description": f"「{current_stage.name}」阶段已停滞 {days_stalled} 天",
                    "stage_name": current_stage.name,
                    "days_stalled": days_stalled,
                })

            # Overdue stage deadline
            if t.template:
                st_def = next((s for s in t.template.stages if s.order == current_stage.order), None)
                if st_def and st_def.deadline_offset_days:
                    deadline = t.created_at + timedelta(days=st_def.deadline_offset_days)
                    if deadline < now and current_stage.status != 'completed':
                        days_overdue = (now - deadline).days
                        alerts.append({
                            "task_id": t.id,
                            "title": t.title,
                            "risk_type": "逾期",
                            "risk_level": "high" if days_overdue > 7 else "medium",
                            "description": f"「{current_stage.name}」阶段截止时间已过 {days_overdue} 天",
                            "stage_name": current_stage.name,
                            "days_overdue": days_overdue,
                        })

        alerts.sort(key=lambda a: a.get("days_stalled", a.get("days_overdue", 0)), reverse=True)
        return alerts[:20]

    # ── Stage Funnel ────────────────────────────────────────────

    async def get_stage_funnel(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(ProjectTask).options(
                selectinload(ProjectTask.stages),
            )
        )
        tasks = result.scalars().all()

        # Collect max stage count across all templates (for stage labels)
        max_order = 0
        stage_counts: dict[int, int] = defaultdict(int)
        for t in tasks:
            for s in t.stages:
                max_order = max(max_order, s.order)
                if s.status in ('in_progress', 'locked'):
                    stage_counts[s.order] += 1

        funnel = []
        for order in range(1, max_order + 1):
            funnel.append({
                "stage_order": order,
                "count": stage_counts.get(order, 0),
            })
        return funnel

    # ── Template Distribution ───────────────────────────────────

    async def get_template_distribution(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(
                TaskTemplate.category,
                func.count(ProjectTask.id).label("cnt"),
            ).join(ProjectTask, ProjectTask.template_id == TaskTemplate.id, isouter=True)
            .group_by(TaskTemplate.category)
        )
        rows = result.all()
        items = []
        for category, cnt in rows:
            label = category or "未分类"
            items.append({"name": label, "count": cnt})
        items.sort(key=lambda x: x["count"], reverse=True)
        return items

    # ── Status Distribution ─────────────────────────────────────

    async def get_status_distribution(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(
                ProjectTask.status,
                func.count(ProjectTask.id).label("cnt"),
            ).group_by(ProjectTask.status)
        )
        status_labels = {
            "pending": "待开始", "active": "进行中",
            "completed": "已完成", "cancelled": "已取消",
        }
        items = []
        for status, cnt in result.all():
            items.append({
                "status": status,
                "label": status_labels.get(status, status),
                "count": cnt,
            })
        return items

    # ── Monthly Trend ───────────────────────────────────────────

    async def get_monthly_trend(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(
                extract("year", ProjectTask.created_at).label("yr"),
                extract("month", ProjectTask.created_at).label("mo"),
                func.count(ProjectTask.id).label("total"),
                func.sum(case((ProjectTask.status == 'completed', 1), else_=0)).label("completed"),
            ).group_by("yr", "mo").order_by("yr", "mo")
        )
        items = []
        for yr, mo, total, completed in result.all():
            items.append({
                "month": f"{int(yr)}-{int(mo):02d}",
                "total": total,
                "completed": completed or 0,
            })
        return items[-12:]  # last 12 months

    # ── Department Workload ─────────────────────────────────────

    async def get_department_workload(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(
                User.department.has(),
                func.count(ProjectTask.id).label("total"),
                func.sum(case((ProjectTask.status == 'completed', 1), else_=0)).label("completed"),
            ).join(User, ProjectTask.creator_id == User.id)
            .group_by(User.department_id)
        )

        dept_names = {}
        user_result = await db.execute(
            select(User).options(selectinload(User.department))
        )
        for u in user_result.scalars().all():
            if u.department_id not in dept_names:
                dept_names[u.department_id] = u.department.name if u.department else "未分配"

        items = []
        for dept_id, total, completed in result.all():
            items.append({
                "department_name": dept_names.get(dept_id, f"部门{dept_id}"),
                "total_tasks": total,
                "completed_tasks": completed or 0,
            })
        items.sort(key=lambda x: x["total_tasks"], reverse=True)
        return items

    # ── Personal Stats ──────────────────────────────────────────

    async def get_personal_stats(self, db: AsyncSession, user_id: int) -> dict:
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # All user's tasks
        result = await db.execute(
            select(ProjectTask).options(
                selectinload(ProjectTask.stages).selectinload(ProjectStage.slots),
                selectinload(ProjectTask.template).selectinload(TaskTemplate.stages),
            ).where(ProjectTask.creator_id == user_id)
            .order_by(ProjectTask.created_at.desc())
        )
        tasks = result.scalars().all()

        total = len(tasks)
        week_completed = sum(1 for t in tasks if t.status == 'completed' and t.updated_at and t.updated_at >= week_start)
        week_total = total

        # Overdue rate: tasks with overdue current stage
        overdue_count = 0
        for t in tasks:
            if t.status not in ('pending', 'active'):
                continue
            cs = next((s for s in t.stages if s.order == t.current_stage_order), None)
            if cs and t.template:
                st_def = next((s for s in t.template.stages if s.order == cs.order), None)
                if st_def and st_def.deadline_offset_days:
                    deadline = t.created_at + timedelta(days=st_def.deadline_offset_days)
                    if deadline < now and cs.status != 'completed':
                        overdue_count += 1
        overdue_rate = round(overdue_count / total * 100, 1) if total else 0.0

        # Average completion days
        completed_tasks = [t for t in tasks if t.status == 'completed' and t.updated_at]
        if completed_tasks:
            avg_days = round(
                sum((t.updated_at - t.created_at).total_seconds() / 86400 for t in completed_tasks) / len(completed_tasks),
                1
            )
        else:
            avg_days = 0.0

        # Streak: consecutive days with at least one completed task (simplified)
        streak = 0
        check_date = now.date()
        while True:
            day_start = datetime(check_date.year, check_date.month, check_date.day, tzinfo=timezone.utc)
            day_end = day_start + timedelta(days=1)
            day_done = any(
                t for t in completed_tasks
                if t.updated_at and day_start <= t.updated_at < day_end
            )
            if day_done:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        # Status distribution
        status_map = defaultdict(int)
        for t in tasks:
            status_map[t.status] += 1
        status_distribution = [
            {"status": k, "label": {"pending": "待开始", "active": "进行中", "completed": "已完成", "cancelled": "已取消"}.get(k, k), "count": v}
            for k, v in status_map.items()
        ]

        return {
            "week_completed_tasks": week_completed,
            "week_total_tasks": week_total,
            "overdue_rate": overdue_rate,
            "avg_completion_days": avg_days,
            "streak_days": streak,
            "total_tasks": total,
            "status_distribution": status_distribution,
        }
