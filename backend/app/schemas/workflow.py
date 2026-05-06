from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TemplateNodeCreate(BaseModel):
    """Create a node within a workflow template."""

    node_name: str = Field(..., description="Display name of the node")
    node_order: int = Field(..., description="Sequential order of this node")
    owner_role: str = Field(..., description="Role responsible for this node (matter_owner, dept_leader, etc.)")
    sla_hours: int | None = Field(default=None, description="SLA timeout in hours, None means no limit")
    required_documents_rule: dict | None = Field(default=None, description="JSON rule defining required documents")
    description: str | None = Field(default=None, description="Optional node description")


class TemplateNodeResponse(BaseModel):
    """Workflow template node information."""

    id: int
    template_id: int
    node_name: str
    node_order: int
    owner_role: str
    sla_hours: int | None = None
    required_documents_rule: dict | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkflowTemplateCreate(BaseModel):
    """Create a new workflow template with its nodes."""

    name: str = Field(..., description="Template name")
    matter_type_id: int = Field(..., description="Matter type this template applies to")
    description: str | None = Field(default=None, description="Optional description")
    nodes: list[TemplateNodeCreate] = Field(default_factory=list, description="Ordered list of template nodes")


class WorkflowTemplateUpdate(BaseModel):
    """Partial update for a workflow template."""

    name: str | None = Field(default=None, description="New template name")
    is_active: bool | None = Field(default=None, description="Whether the template is active")
    description: str | None = Field(default=None, description="New description")


class WorkflowTemplateResponse(BaseModel):
    """Workflow template information."""

    id: int
    name: str
    matter_type_id: int
    matter_type_name: str
    is_active: bool = True
    description: str | None = None
    node_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowNodeResponse(BaseModel):
    """Active workflow node on a matter."""

    id: int
    matter_id: int
    node_name: str
    node_order: int
    owner_id: int
    owner_name: str
    status: str
    sla_status: str | None = None
    planned_finish_time: datetime | None = None
    actual_finish_time: datetime | None = None
    description: str | None = None
    required_documents_rule: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeAdvanceRequest(BaseModel):
    """Request to advance to the next workflow node."""

    comment: str | None = Field(default=None, description="Optional comment when advancing the node")


class NodeValidationResponse(BaseModel):
    """Validation result for a workflow node."""

    valid: bool = Field(..., description="Whether the node passes validation")
    missing_documents: list[str] = Field(default_factory=list, description="List of missing document names")
    warnings: list[str] = Field(default_factory=list, description="List of validation warnings")
