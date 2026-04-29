from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, check_permission
from app.core.permissions import Permission
from app.core.pagination import PaginationParams
from app.models.user import User
from app.services.webhook_service import webhook_service

router = APIRouter()


# ---------- Schemas ----------

class WebhookCreate(BaseModel):
    name: str
    url: str
    events: list[str]
    is_active: bool = True


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class WebhookOut(BaseModel):
    id: int
    name: str
    url: str
    events: str
    is_active: bool
    last_triggered_at: str | None
    last_status: str | None
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    items: list[WebhookOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------- Routes ----------

@router.post("/", response_model=WebhookOut)
async def create_webhook(
    data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await webhook_service.create(db, current_user.id, data)
    return WebhookOut(
        id=sub.id, name=sub.name, url=sub.url,
        events=sub.events, is_active=sub.is_active,
        last_triggered_at=sub.last_triggered_at.isoformat() if sub.last_triggered_at else None,
        last_status=sub.last_status,
        created_at=sub.created_at.isoformat() if sub.created_at else None,
        updated_at=sub.updated_at.isoformat() if sub.updated_at else None,
    )


@router.get("/", response_model=WebhookListResponse)
async def list_webhooks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    items, total = await webhook_service.get_list(db, current_user.id, pagination)

    result_items = [
        WebhookOut(
            id=sub.id, name=sub.name, url=sub.url,
            events=sub.events, is_active=sub.is_active,
            last_triggered_at=sub.last_triggered_at.isoformat() if sub.last_triggered_at else None,
            last_status=sub.last_status,
            created_at=sub.created_at.isoformat() if sub.created_at else None,
            updated_at=sub.updated_at.isoformat() if sub.updated_at else None,
        )
        for sub in items
    ]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return WebhookListResponse(
        items=result_items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@router.get("/{sub_id}", response_model=WebhookOut)
async def get_webhook(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await webhook_service.get(db, sub_id, current_user.id)
    return WebhookOut(
        id=sub.id, name=sub.name, url=sub.url,
        events=sub.events, is_active=sub.is_active,
        last_triggered_at=sub.last_triggered_at.isoformat() if sub.last_triggered_at else None,
        last_status=sub.last_status,
        created_at=sub.created_at.isoformat() if sub.created_at else None,
        updated_at=sub.updated_at.isoformat() if sub.updated_at else None,
    )


@router.put("/{sub_id}", response_model=WebhookOut)
async def update_webhook(
    sub_id: int,
    data: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await webhook_service.update(db, sub_id, current_user.id, data)
    return WebhookOut(
        id=sub.id, name=sub.name, url=sub.url,
        events=sub.events, is_active=sub.is_active,
        last_triggered_at=sub.last_triggered_at.isoformat() if sub.last_triggered_at else None,
        last_status=sub.last_status,
        created_at=sub.created_at.isoformat() if sub.created_at else None,
        updated_at=sub.updated_at.isoformat() if sub.updated_at else None,
    )


@router.post("/{sub_id}/regenerate-secret")
async def regenerate_secret(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_secret = await webhook_service.regenerate_secret(db, sub_id, current_user.id)
    return {"secret": new_secret}


@router.delete("/{sub_id}")
async def delete_webhook(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await webhook_service.delete(db, sub_id, current_user.id)
    return {"detail": "Webhook deleted"}
