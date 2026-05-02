"""Dashboard API routes — overview, trends, analytics, personal stats."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.dashboard_service import DashboardService

router = APIRouter()
_service = DashboardService()


# ── Schemas ──────────────────────────────────────────────────────

class OverviewOut(BaseModel):
    total_tasks: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0
    pipeline_progress: float = 0.0
    overdue_stages: int = 0
    total_slots: int = 0
    filled_slots: int = 0
    total_documents: int = 0


class KeyProjectOut(BaseModel):
    task_id: int
    title: str
    template_name: str
    current_stage: str
    current_stage_order: int
    progress: float
    status: str
    creator_id: int
    created_at: str | None


class RiskAlertOut(BaseModel):
    task_id: int
    title: str
    risk_type: str
    risk_level: str
    description: str
    stage_name: str


class DistributionOut(BaseModel):
    name: str
    count: int


class TrendOut(BaseModel):
    month: str
    total: int
    completed: int


class WorkloadOut(BaseModel):
    department_name: str
    total_tasks: int
    completed_tasks: int


class PersonalStatsOut(BaseModel):
    week_completed_tasks: int = 0
    week_total_tasks: int = 0
    overdue_rate: float = 0.0
    avg_completion_days: float = 0.0
    streak_days: int = 0
    total_tasks: int = 0
    status_distribution: list[dict] = []


class AdvancedAnalyticsOut(BaseModel):
    monthly_trend: list[TrendOut]
    department_workload: list[WorkloadOut]
    template_distribution: list[DistributionOut]
    status_distribution: list[dict]


# ── Routes ───────────────────────────────────────────────────────

@router.get("/overview", response_model=OverviewOut)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard overview — total tasks, completion rate, pipeline progress."""
    return await _service.get_overview(db)


@router.get("/key-projects", response_model=list[KeyProjectOut])
async def get_key_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Active projects/tasks with progress info."""
    return await _service.get_active_tasks(db)


@router.get("/risks", response_model=list[RiskAlertOut])
async def get_risk_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Risk alerts — stalled and overdue stages."""
    return await _service.get_risk_alerts(db)


@router.get("/progress-chart")
async def get_progress_chart(
    period: str = Query("monthly"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Progress chart data — stage funnel + monthly trend."""
    funnel = await _service.get_stage_funnel(db)
    trend = await _service.get_monthly_trend(db)
    return {"funnel": funnel, "trend": trend}


@router.get("/type-distribution", response_model=list[DistributionOut])
async def get_type_distribution(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Task type/template distribution."""
    return await _service.get_template_distribution(db)


@router.get("/personal-stats", response_model=PersonalStatsOut)
async def get_personal_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Personal efficiency stats for the current user."""
    return await _service.get_personal_stats(db, current_user.id)


@router.get("/advanced", response_model=AdvancedAnalyticsOut)
async def get_advanced_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Advanced analytics — trends + workload + distributions."""
    trend = await _service.get_monthly_trend(db)
    workload = await _service.get_department_workload(db)
    tmpl_dist = await _service.get_template_distribution(db)
    status_dist = await _service.get_status_distribution(db)
    return AdvancedAnalyticsOut(
        monthly_trend=trend,
        department_workload=workload,
        template_distribution=tmpl_dist,
        status_distribution=status_dist,
    )
