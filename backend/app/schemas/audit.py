from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


class AuditLogResponse(BaseModel):
    """Audit/operation log entry."""

    id: int
    user_id: int
    user_name: str
    operation_type: str
    target_type: str
    target_id: int | None = None
    detail: str | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(PaginatedResponse["AuditLogResponse"]):
    """Paginated list of audit logs."""

    pass


class AuditLogFilter(BaseModel):
    """Filter parameters for audit log queries."""

    user_id: int | None = Field(default=None, description="Filter by user ID")
    operation_type: str | None = Field(default=None, description="Filter by operation type")
    target_type: str | None = Field(default=None, description="Filter by target entity type")
    start_date: datetime | None = Field(default=None, description="Filter logs after this date (inclusive)")
    end_date: datetime | None = Field(default=None, description="Filter logs before this date (inclusive)")
