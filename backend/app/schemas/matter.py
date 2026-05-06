from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


class MatterMemberResponse(BaseModel):
    """Matter member information."""

    id: int
    user_id: int
    user_name: str
    role_in_matter: str
    avatar_url: str | None = None
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatterMemberAdd(BaseModel):
    """Add members to a matter."""

    user_ids: list[int] = Field(..., description="List of user IDs to add as members")
    role_in_matter: str = Field(default="collaborator", description="Role assigned to all new members")


class MatterCommentCreate(BaseModel):
    """Create a new comment on a matter."""

    content: str = Field(..., description="Comment text")


class MatterCommentResponse(BaseModel):
    """Matter comment information."""

    id: int
    matter_id: int
    user_id: int
    user_name: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatterStatusUpdate(BaseModel):
    """Update the status of a matter."""

    status: str = Field(..., description="New status value")
    comment: str | None = Field(default=None, description="Optional comment explaining the status change")


class MatterCreate(BaseModel):
    """Create a new matter."""

    title: str = Field(..., description="Matter title")
    type_id: int = Field(..., description="Matter type ID")
    owner_id: int = Field(..., description="Owner user ID")
    description: str | None = Field(default=None, description="Optional description")
    is_key_project: bool = Field(default=False, description="Whether this is a key/key project")
    due_date: datetime | None = Field(default=None, description="Expected completion date")
    member_ids: list[int] = Field(default_factory=list, description="Initial member user IDs")
    workflow_template_id: int | None = Field(default=None, description="Workflow template ID to initialize nodes from")


class MatterUpdate(BaseModel):
    """Partial update for an existing matter."""

    title: str | None = Field(default=None, description="New title")
    is_key_project: bool | None = Field(default=None, description="Whether this is a key project")
    due_date: datetime | None = Field(default=None, description="New expected completion date")
    description: str | None = Field(default=None, description="New description")


class MatterResponse(BaseModel):
    """Matter information (summary/list view)."""

    id: int
    matter_no: str
    title: str
    type_id: int
    type_name: str
    owner_id: int
    owner_name: str
    status: str
    is_key_project: bool = False
    progress: float = 0.0
    current_node_id: int | None = None
    current_node_name: str | None = None
    due_date: datetime | None = None
    description: str | None = None
    member_count: int = 0
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatterDetailResponse(MatterResponse):
    """Matter detail view (includes nested related data)."""

    members: list[MatterMemberResponse] = Field(default_factory=list)
    documents: list = Field(default_factory=list)  # list[DocumentResponse] - lazy import avoided
    nodes: list = Field(default_factory=list)  # list[WorkflowNodeResponse] - lazy import avoided
    recent_comments: list[MatterCommentResponse] = Field(default_factory=list)


class MatterListResponse(PaginatedResponse["MatterResponse"]):
    """Paginated list of matters."""

    pass


class MatterFilter(BaseModel):
    """Filter parameters for matter listing."""

    type_id: int | None = Field(default=None, description="Filter by matter type")
    status: str | None = Field(default=None, description="Filter by status")
    owner_id: int | None = Field(default=None, description="Filter by owner user ID")
    is_key_project: bool | None = Field(default=None, description="Filter by key project flag")
    keyword: str | None = Field(default=None, description="Full-text search on title and description")
