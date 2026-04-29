from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


class NotificationResponse(BaseModel):
    """Notification information."""

    id: int
    user_id: int
    type: str
    title: str
    content: str | None = None
    is_read: bool = False
    related_matter_id: int | None = None
    related_matter_title: str | None = None
    created_at: str  # ISODate string or datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(PaginatedResponse["NotificationResponse"]):
    """Paginated list of notifications."""

    pass


class NotificationCountResponse(BaseModel):
    """Count of total and unread notifications."""

    total: int = Field(..., description="Total number of notifications")
    unread: int = Field(..., description="Number of unread notifications")
