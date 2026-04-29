from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardOverview(BaseModel):
    """Dashboard overview statistics."""

    total_matters: int = Field(default=0, description="Total number of matters")
    in_progress_matters: int = Field(default=0, description="Number of matters currently in progress")
    overdue_matters: int = Field(default=0, description="Number of matters past their due date")
    completed_matters: int = Field(default=0, description="Number of completed matters")
    completion_rate: float = Field(default=0.0, description="Completion rate as a percentage (0-100)")
    total_documents: int = Field(default=0, description="Total number of documents")
    pending_tasks: int = Field(default=0, description="Number of pending tasks")
    risk_count: int = Field(default=0, description="Number of matters flagged at risk")


class KeyProjectItem(BaseModel):
    """A key project entry for the dashboard."""

    matter_id: int
    matter_no: str
    title: str
    owner_name: str
    progress: float = 0.0
    status: str
    current_node: str | None = None
    due_date: datetime | None = None
    risk_level: str = Field(default="normal", description="Risk level: normal, warning, critical")


class RiskAlertItem(BaseModel):
    """A risk alert entry for the dashboard."""

    matter_id: int
    matter_no: str
    title: str
    risk_type: str = Field(..., description="Type of risk: overdue, stalled, blocked, etc.")
    risk_level: str = Field(..., description="Risk level: warning, critical")
    description: str = Field(..., description="Human-readable risk description")
    days_overdue: int | None = Field(default=None, description="Number of days past due (if applicable)")


class ProgressChartData(BaseModel):
    """Data for a progress chart widget."""

    labels: list[str] = Field(default_factory=list, description="Chart labels (e.g., month names)")
    completed: list[int] = Field(default_factory=list, description="Completed counts per label")
    in_progress: list[int] = Field(default_factory=list, description="In-progress counts per label")
    pending: list[int] = Field(default_factory=list, description="Pending counts per label")


class TypeDistributionData(BaseModel):
    """Data point for matter type distribution chart."""

    name: str = Field(..., description="Type name")
    count: int = Field(..., description="Number of matters of this type")
    percentage: float = Field(..., description="Percentage of total")
