from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


class TaskCreate(BaseModel):
    """Create a new task."""

    matter_id: int = Field(..., description="Associated matter ID")
    title: str = Field(..., description="Task title")
    assignee_id: int = Field(..., description="Assigned user ID")
    priority: str = Field(default="normal", description="Priority: low, normal, high, urgent")
    due_time: datetime | None = Field(default=None, description="Task deadline")
    description: str | None = Field(default=None, description="Optional task description")
    node_id: int | None = Field(default=None, description="Associated workflow node ID")


class TaskUpdate(BaseModel):
    """Partial update for an existing task."""

    title: str | None = Field(default=None, description="New task title")
    assignee_id: int | None = Field(default=None, description="New assignee user ID")
    status: str | None = Field(default=None, description="New status: pending, in_progress, completed, cancelled")
    priority: str | None = Field(default=None, description="New priority: low, normal, high, urgent")
    due_time: datetime | None = Field(default=None, description="New deadline")


class TaskResponse(BaseModel):
    """Task information."""

    id: int
    matter_id: int
    matter_title: str
    node_id: int | None = None
    node_name: str | None = None
    title: str
    assigner_id: int
    assigner_name: str
    assignee_id: int
    assignee_name: str
    status: str
    priority: str
    due_time: datetime | None = None
    description: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(PaginatedResponse["TaskResponse"]):
    """Paginated list of tasks."""

    pass


class TaskFilter(BaseModel):
    """Filter parameters for task listing."""

    status: str | None = Field(default=None, description="Filter by status")
    priority: str | None = Field(default=None, description="Filter by priority")
    assignee_id: int | None = Field(default=None, description="Filter by assignee user ID")
    matter_id: int | None = Field(default=None, description="Filter by associated matter ID")
