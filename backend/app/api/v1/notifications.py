from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.core.pagination import PaginationParams
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter()


# ---------- Pydantic Schemas ----------

class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    content: str | None
    is_read: bool
    created_at: str | None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: list[NotificationOut]
    total: int
    page: int
    page_size: int
    total_pages: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


# ---------- Routes ----------

@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    is_read: bool = Query(None),
    notification_type: str = Query(None, alias="type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    service = NotificationService()
    items, total = await service.get_notifications(
        db, current_user.id, pagination,
        is_read=is_read, notification_type=notification_type,
    )
    unread_count = await service.get_unread_count(db, current_user.id)

    result_items = [
        NotificationOut(
            id=n.id,
            type=n.type,
            title=n.title,
            content=n.content,
            is_read=n.is_read,
            created_at=n.created_at.isoformat() if n.created_at else None,
        )
        for n in items
    ]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return NotificationListResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await NotificationService().get_unread_count(db, current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NotificationService().mark_as_read(db, notification_id, current_user.id)
    return {"detail": "Notification marked as read"}


@router.put("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NotificationService().mark_all_as_read(db, current_user.id)
    return {"detail": "All notifications marked as read"}


class BatchIdsRequest(BaseModel):
    ids: list[int]


@router.post("/batch/read")
async def batch_mark_read(
    data: BatchIdsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await NotificationService().batch_mark_read(db, data.ids, current_user.id)
    return {"detail": f"已标记 {count} 条为已读", "count": count}
