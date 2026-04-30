"""Public dashboard API — no authentication required, aggregate data only."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/public/dashboard", tags=["public-dashboard"])
_service = DashboardService()


# ── Schemas ────────────────────────────────────────────────────

class OverviewStats(BaseModel):
    total_tasks: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0
    pipeline_progress: float = 0.0
    overdue_stages: int = 0
    total_slots: int = 0
    filled_slots: int = 0
    total_documents: int = 0


class ActiveTaskItem(BaseModel):
    task_id: int
    title: str
    template_name: str
    current_stage: str
    current_stage_order: int
    progress: float
    status: str
    creator_id: int
    created_at: str | None


class RiskAlertItem(BaseModel):
    task_id: int
    title: str
    risk_type: str
    risk_level: str
    description: str
    stage_name: str | None = None
    days_stalled: int | None = None
    days_overdue: int | None = None


class StageFunnelItem(BaseModel):
    stage_order: int
    count: int


class TemplateDistItem(BaseModel):
    name: str
    count: int


class StatusDistItem(BaseModel):
    status: str
    label: str
    count: int


class MonthlyTrendItem(BaseModel):
    month: str
    total: int
    completed: int


class DeptWorkloadItem(BaseModel):
    department_name: str
    total_tasks: int
    completed_tasks: int


# ── Routes ─────────────────────────────────────────────────────

@router.get("/overview", response_model=OverviewStats)
async def get_overview(db: AsyncSession = Depends(get_db)):
    return await _service.get_overview(db)


@router.get("/active-tasks", response_model=list[ActiveTaskItem])
async def get_active_tasks(db: AsyncSession = Depends(get_db)):
    return await _service.get_active_tasks(db)


@router.get("/risks", response_model=list[RiskAlertItem])
async def get_risks(db: AsyncSession = Depends(get_db)):
    return await _service.get_risk_alerts(db)


@router.get("/stage-funnel", response_model=list[StageFunnelItem])
async def get_stage_funnel(db: AsyncSession = Depends(get_db)):
    return await _service.get_stage_funnel(db)


@router.get("/template-distribution", response_model=list[TemplateDistItem])
async def get_template_distribution(db: AsyncSession = Depends(get_db)):
    return await _service.get_template_distribution(db)


@router.get("/analytics", response_model=dict)
async def get_analytics(db: AsyncSession = Depends(get_db)):
    from asyncio import gather
    monthly_trend, template_dist, status_dist, stage_funnel, departments = await gather(
        _service.get_monthly_trend(db),
        _service.get_template_distribution(db),
        _service.get_status_distribution(db),
        _service.get_stage_funnel(db),
        _service.get_department_workload(db),
    )
    return {
        "monthly_trend": monthly_trend,
        "template_distribution": template_dist,
        "status_distribution": status_dist,
        "stage_funnel": stage_funnel,
        "departments": departments,
    }
