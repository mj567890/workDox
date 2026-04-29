"""Public dashboard API — no authentication required, aggregate data only."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies import get_db
from app.core.cache import cache
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/public/dashboard", tags=["public-dashboard"])
dashboard_service = DashboardService()


# ---------- Pydantic Schemas ----------

class PublicOverviewStats(BaseModel):
    total_matters: int
    total_documents: int
    completed_matters: int
    in_progress_matters: int
    overdue_matters: int
    completion_rate: float


class PublicKeyProject(BaseModel):
    matter_id: int
    matter_no: str
    title: str
    progress: float
    status: str
    owner_name: str | None
    due_date: str | None
    risk_level: str = "low"


class PublicRiskAlert(BaseModel):
    matter_id: int
    matter_no: str
    title: str
    risk_type: str
    risk_level: str
    description: str = ""


class PublicProgressChartOut(BaseModel):
    labels: list[str]
    completed: list[int]
    in_progress: list[int]
    pending: list[int]


class PublicTypeDistributionItem(BaseModel):
    name: str
    count: int
    percentage: float


class PublicMonthlyTrend(BaseModel):
    month: str
    total: int
    completed: int
    overdue: int


class PublicDepartmentWorkload(BaseModel):
    department_name: str
    total_matters: int
    completed_matters: int
    overdue_matters: int
    avg_progress: float


class PublicAdvancedAnalyticsOut(BaseModel):
    departments: list[PublicDepartmentWorkload]
    monthly_trend: list[PublicMonthlyTrend]
    priority_breakdown: list[dict]


# ---------- Routes ----------

@router.get("/overview", response_model=PublicOverviewStats)
async def public_get_overview(db: AsyncSession = Depends(get_db)):
    """Get aggregate overview stats for the public dashboard."""
    cache_key = "public:dashboard:overview"
    cached = await cache.get(cache_key)
    if cached:
        return PublicOverviewStats(**cached)

    data = await dashboard_service.get_overview(db, matter_ids=None)
    result = PublicOverviewStats(
        total_matters=data["total_matters"],
        total_documents=data["total_documents"],
        completed_matters=data["completed_matters"],
        in_progress_matters=data["in_progress_matters"],
        overdue_matters=data["overdue_matters"],
        completion_rate=data["completion_rate"],
    )
    await cache.set(cache_key, result.model_dump(), ttl=120)
    return result


@router.get("/key-projects", response_model=list[PublicKeyProject])
async def public_get_key_projects(db: AsyncSession = Depends(get_db)):
    """Get key projects for the public dashboard."""
    cache_key = "public:dashboard:key_projects"
    cached = await cache.get(cache_key)
    if cached:
        return [PublicKeyProject(**item) for item in cached]

    data = await dashboard_service.get_key_projects(db, matter_ids=None)
    result = [PublicKeyProject(**item) for item in data]
    await cache.set(cache_key, [r.model_dump() for r in result], ttl=120)
    return result


@router.get("/risks", response_model=list[PublicRiskAlert])
async def public_get_risks(db: AsyncSession = Depends(get_db)):
    """Get risk alerts for the public dashboard."""
    cache_key = "public:dashboard:risks"
    cached = await cache.get(cache_key)
    if cached:
        return [PublicRiskAlert(**item) for item in cached]

    data = await dashboard_service.get_risk_alerts(db, matter_ids=None)
    result = [PublicRiskAlert(**item) for item in data]
    await cache.set(cache_key, [r.model_dump() for r in result], ttl=120)
    return result


@router.get("/progress-chart", response_model=PublicProgressChartOut)
async def public_get_progress_chart(db: AsyncSession = Depends(get_db)):
    """Get progress chart data for the public dashboard."""
    cache_key = "public:dashboard:progress_chart"
    cached = await cache.get(cache_key)
    if cached:
        return PublicProgressChartOut(**cached)

    data = await dashboard_service.get_progress_chart(db, matter_ids=None)
    result = PublicProgressChartOut(**data)
    await cache.set(cache_key, result.model_dump(), ttl=120)
    return result


@router.get("/type-distribution", response_model=list[PublicTypeDistributionItem])
async def public_get_type_distribution(db: AsyncSession = Depends(get_db)):
    """Get type distribution for the public dashboard."""
    cache_key = "public:dashboard:type_distribution"
    cached = await cache.get(cache_key)
    if cached:
        return [PublicTypeDistributionItem(**item) for item in cached]

    data = await dashboard_service.get_type_distribution(db, matter_ids=None)
    result = [PublicTypeDistributionItem(**item) for item in data]
    await cache.set(cache_key, [r.model_dump() for r in result], ttl=120)
    return result


@router.get("/advanced", response_model=PublicAdvancedAnalyticsOut)
async def public_get_advanced_analytics(db: AsyncSession = Depends(get_db)):
    """Get advanced analytics for the public dashboard (department, trends, priority)."""
    cache_key = "public:dashboard:advanced"
    cached = await cache.get(cache_key)
    if cached:
        return PublicAdvancedAnalyticsOut(**cached)

    from sqlalchemy import case, extract
    from datetime import datetime, timedelta, timezone
    from app.models.user import User
    from app.models.matter import Matter
    from app.models.department import Department
    from app.models.task import Task

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
        .group_by(Department.name)
        .order_by(func.count(Matter.id).desc())
    )
    dept_result = await db.execute(dept_query)
    dept_rows = dept_result.all()

    departments = [
        PublicDepartmentWorkload(
            department_name=row[0] or "未分配",
            total_matters=row[1],
            completed_matters=row[2] or 0,
            overdue_matters=row[3] or 0,
            avg_progress=round(row[4] or 0, 1),
        )
        for row in dept_rows
    ]

    # Monthly trend (last 12 months)
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
        .group_by("yr", "mo")
        .order_by("yr", "mo")
    )
    monthly_result = await db.execute(monthly_query)
    monthly_trend = [
        PublicMonthlyTrend(
            month=f"{int(row[0])}-{int(row[1]):02d}",
            total=row[2],
            completed=row[3] or 0,
            overdue=row[4] or 0,
        )
        for row in monthly_result.all()
    ]

    # Priority breakdown (aggregate, not per-user)
    priority_query = (
        select(Task.priority, func.count(Task.id).label("count"))
        .group_by(Task.priority)
    )
    priority_result = await db.execute(priority_query)
    priority_breakdown = [
        {"priority": row[0], "count": row[1]}
        for row in priority_result.all()
    ]

    result = PublicAdvancedAnalyticsOut(
        departments=departments,
        monthly_trend=monthly_trend,
        priority_breakdown=priority_breakdown,
    )
    await cache.set(cache_key, result.model_dump(), ttl=120)
    return result
