from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

from app.dependencies import get_current_user, get_db, check_permission
from app.core.cache import cache
from app.core.permissions import Permission, RoleCode
from sqlalchemy import case

from app.models.user import User
from app.models.matter import Matter, MatterMember
from app.models.department import Department
from app.models.task import Task
from app.services.dashboard_service import DashboardService

router = APIRouter()
dashboard_service = DashboardService()


# ---------- Pydantic Schemas ----------

class OverviewStats(BaseModel):
    total_matters: int
    total_documents: int
    pending_tasks: int
    completed_matters: int
    in_progress_matters: int
    overdue_matters: int
    completion_rate: float
    risk_count: int


class KeyProject(BaseModel):
    matter_id: int
    matter_no: str
    title: str
    progress: float
    status: str
    current_node: str | None
    owner_name: str | None
    due_date: str | None
    risk_level: str = "low"


class RiskAlert(BaseModel):
    matter_id: int
    matter_no: str
    title: str
    risk_type: str  # overdue, near_deadline, stalled
    risk_level: str  # high, medium, low
    description: str = ""
    days_overdue: int | None = None


class ProgressChartOut(BaseModel):
    labels: list[str]
    completed: list[int]
    in_progress: list[int]
    pending: list[int]


class TypeDistributionItem(BaseModel):
    name: str
    count: int
    percentage: float


class PersonalStats(BaseModel):
    week_completed_tasks: int = 0
    week_total_tasks: int = 0
    overdue_rate: float = 0.0
    avg_completion_days: float = 0.0
    streak_days: int = 0
    priority_distribution: list[dict] = []  # [{priority: "high", count: 3}, ...]


# ---------- Helper Functions ----------

async def _get_user_matter_ids(user: User, db: AsyncSession) -> list[int] | None:
    """Return list of visible matter IDs, or None if user is admin (sees all)."""
    role_codes = [r.role_code for r in (user.roles or []) if hasattr(r, 'role_code')]
    if RoleCode.ADMIN in role_codes:
        return None  # None = no filter, admin sees all

    member_result = await db.execute(
        select(MatterMember.matter_id).where(MatterMember.user_id == user.id)
    )
    member_ids = [row[0] for row in member_result.all()]

    if RoleCode.DEPT_LEADER in role_codes:
        from app.models.document import Matter as M, Document as D
        dept_result = await db.execute(
            select(Matter.id).join(User, Matter.owner_id == User.id).where(
                User.department_id == user.department_id
            )
        )
        dept_ids = [row[0] for row in dept_result.all()]
        member_ids = list(set(member_ids + dept_ids))

    return member_ids


# ---------- Routes ----------

@router.get("/overview", response_model=OverviewStats)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.DASHBOARD_VIEW)),
):
    cache_key = f"dashboard:overview:user:{current_user.id}"
    cached = await cache.get(cache_key)
    if cached:
        return OverviewStats(**cached)

    matter_ids = await _get_user_matter_ids(current_user, db)
    data = await dashboard_service.get_overview(db, matter_ids=matter_ids)

    # Augment with per-user pending task count
    pending_tasks = (
        await db.execute(
            select(func.count(Task.id)).where(
                Task.assignee_id == current_user.id,
                Task.status.in_(["pending", "in_progress"]),
            )
        )
    ).scalar() or 0
    data["pending_tasks"] = pending_tasks

    result = OverviewStats(**data)
    await cache.set(cache_key, result.model_dump(), ttl=300)
    return result


@router.get("/key-projects", response_model=list[KeyProject])
async def get_key_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.DASHBOARD_VIEW)),
):
    cache_key = f"dashboard:key_projects:user:{current_user.id}"
    cached = await cache.get(cache_key)
    if cached:
        return [KeyProject(**item) for item in cached]

    matter_ids = await _get_user_matter_ids(current_user, db)
    data = await dashboard_service.get_key_projects(db, matter_ids=matter_ids)

    result = [KeyProject(**item) for item in data]
    await cache.set(cache_key, [kp.model_dump() for kp in result], ttl=300)
    return result


@router.get("/risks", response_model=list[RiskAlert])
async def get_risks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.DASHBOARD_VIEW)),
):
    cache_key = f"dashboard:risks:user:{current_user.id}"
    cached = await cache.get(cache_key)
    if cached:
        return [RiskAlert(**item) for item in cached]

    matter_ids = await _get_user_matter_ids(current_user, db)
    data = await dashboard_service.get_risk_alerts(db, matter_ids=matter_ids)

    result = [RiskAlert(**item) for item in data]
    await cache.set(cache_key, [r.model_dump() for r in result], ttl=300)
    return result


@router.get("/progress-chart", response_model=ProgressChartOut)
async def get_progress_chart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.DASHBOARD_VIEW)),
):
    cache_key = f"dashboard:progress_chart:user:{current_user.id}"
    cached = await cache.get(cache_key)
    if cached:
        return ProgressChartOut(**cached)

    matter_ids = await _get_user_matter_ids(current_user, db)
    data = await dashboard_service.get_progress_chart(db, matter_ids=matter_ids)

    result = ProgressChartOut(**data)
    await cache.set(cache_key, result.model_dump(), ttl=300)
    return result


@router.get("/type-distribution", response_model=list[TypeDistributionItem])
async def get_type_distribution(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.DASHBOARD_VIEW)),
):
    cache_key = f"dashboard:type_distribution:user:{current_user.id}"
    cached = await cache.get(cache_key)
    if cached:
        return [TypeDistributionItem(**item) for item in cached]

    matter_ids = await _get_user_matter_ids(current_user, db)
    data = await dashboard_service.get_type_distribution(db, matter_ids=matter_ids)

    result = [TypeDistributionItem(**item) for item in data]
    await cache.set(cache_key, [item.model_dump() for item in result], ttl=300)
    return result


# ---------- Advanced Analytics ----------

class DepartmentWorkload(BaseModel):
    department_name: str
    total_matters: int
    completed_matters: int
    overdue_matters: int
    avg_progress: float
    workload_score: float  # 0-100 normalized workload indicator


class MonthlyTrend(BaseModel):
    month: str  # YYYY-MM
    total: int
    completed: int
    overdue: int


class TrendComparison(BaseModel):
    current: list[MonthlyTrend]
    previous: list[MonthlyTrend]


class AdvancedAnalyticsOut(BaseModel):
    departments: list[DepartmentWorkload]
    monthly_trend: list[MonthlyTrend]
    priority_breakdown: list[dict]  # [{priority: "high", count: 10}, ...]


@router.get("/advanced", response_model=AdvancedAnalyticsOut)
async def get_advanced_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.DASHBOARD_VIEW)),
):
    cache_key = f"dashboard:advanced:user:{current_user.id}"
    cached = await cache.get(cache_key)
    if cached:
        return AdvancedAnalyticsOut(**cached)

    matter_ids = await _get_user_matter_ids(current_user, db)

    # Department workload
    dept_query = (
        select(
            Department.name,
            func.count(Matter.id).label("total"),
            func.sum(case((Matter.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Matter.status == "overdue", 1), else_=0)).label("overdue"),
            func.avg(Matter.progress).label("avg_progress"),
        )
        .join(User, Matter.owner_id == User.id)
        .join(Department, User.department_id == Department.id, isouter=True)
    )
    if matter_ids is not None:
        dept_query = dept_query.where(Matter.id.in_(matter_ids))
    dept_query = dept_query.group_by(Department.name).order_by(func.count(Matter.id).desc())
    dept_result = await db.execute(dept_query)
    dept_rows = dept_result.all()

    max_total = max((row[1] for row in dept_rows), default=1)
    departments = [
        DepartmentWorkload(
            department_name=row[0] or "未分配",
            total_matters=row[1],
            completed_matters=row[2] or 0,
            overdue_matters=row[3] or 0,
            avg_progress=round(row[4] or 0, 1),
            workload_score=round((row[1] / max_total) * 100, 1),
        )
        for row in dept_rows
    ]

    # Monthly trend (last 12 months)
    from sqlalchemy import extract
    twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=365)
    monthly_query = (
        select(
            extract("year", Matter.created_at).label("yr"),
            extract("month", Matter.created_at).label("mo"),
            func.count(Matter.id).label("total"),
            func.sum(case((Matter.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Matter.status == "overdue", 1), else_=0)).label("overdue"),
        )
        .where(Matter.created_at >= twelve_months_ago)
    )
    if matter_ids is not None:
        monthly_query = monthly_query.where(Matter.id.in_(matter_ids))
    monthly_query = monthly_query.group_by("yr", "mo").order_by("yr", "mo")
    monthly_result = await db.execute(monthly_query)
    monthly_trend = [
        MonthlyTrend(
            month=f"{int(row[0])}-{int(row[1]):02d}",
            total=row[2],
            completed=row[3] or 0,
            overdue=row[4] or 0,
        )
        for row in monthly_result.all()
    ]

    # Priority breakdown from tasks
    priority_query = (
        select(
            Task.priority,
            func.count(Task.id).label("count"),
        )
        .where(Task.assignee_id == current_user.id)
        .group_by(Task.priority)
    )
    priority_result = await db.execute(priority_query)
    priority_breakdown = [
        {"priority": row[0], "count": row[1]}
        for row in priority_result.all()
    ]

    result = AdvancedAnalyticsOut(
        departments=departments,
        monthly_trend=monthly_trend,
        priority_breakdown=priority_breakdown,
    )
    await cache.set(cache_key, result.model_dump(), ttl=600)
    return result


# ---------- Personal Stats ----------

@router.get("/personal-stats", response_model=PersonalStats)
async def get_personal_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await dashboard_service.get_personal_stats(db, user_id=current_user.id)
    return PersonalStats(**data)
