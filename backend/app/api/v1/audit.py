from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, check_permission
from app.core.permissions import Permission
from app.core.pagination import PaginationParams
from app.models.user import User
from app.services.audit_service import AuditService

router = APIRouter()


# ---------- Pydantic Schemas ----------

class AuditLogOut(BaseModel):
    id: int
    user_id: int
    username: str | None
    operation_type: str
    target_type: str
    target_id: int | None
    detail: str | None
    ip_address: str | None
    created_at: str | None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------- Routes ----------

@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    user_id: int = Query(None),
    operation_type: str = Query(None),
    target_type: str = Query(None),
    target_id: int = Query(None),
    keyword: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_AUDIT_VIEW)),
):
    from datetime import datetime

    start_date = None
    end_date = None
    if date_from:
        try:
            start_date = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        except ValueError:
            pass
    if date_to:
        try:
            end_date = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except ValueError:
            pass

    filters = dict(
        user_id=user_id,
        operation_type=operation_type,
        target_type=target_type,
        target_id=target_id,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
    )
    pagination = PaginationParams(page=page, page_size=page_size)
    service = AuditService()
    items, total = await service.get_logs(db, pagination, filters)

    result_items = [
        AuditLogOut(
            id=log.id,
            user_id=log.user_id,
            username=log.user.username if log.user else None,
            operation_type=log.operation_type,
            target_type=log.target_type,
            target_id=log.target_id,
            detail=log.detail,
            ip_address=log.ip_address,
            created_at=log.created_at.isoformat() if log.created_at else None,
        )
        for log in items
    ]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return AuditLogListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
