from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.dashboard_service import DashboardService

router = APIRouter()
_service = DashboardService()


class PersonalStatsOut(BaseModel):
    week_completed_tasks: int = 0
    week_total_tasks: int = 0
    overdue_rate: float = 0.0
    avg_completion_days: float = 0.0
    streak_days: int = 0
    total_tasks: int = 0
    status_distribution: list[dict] = []


@router.get("/personal-stats", response_model=PersonalStatsOut)
async def get_personal_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _service.get_personal_stats(db, current_user.id)
