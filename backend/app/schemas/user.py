from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


class RoleInfo(BaseModel):
    """Role information reference (used in nested responses)."""

    id: int
    role_name: str
    role_code: str

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    """Create a new role."""

    role_name: str = Field(..., description="Display name of the role")
    role_code: str = Field(..., description="Unique code identifier for the role")
    description: str | None = Field(default=None, description="Optional description")


class RoleUpdate(BaseModel):
    """Update an existing role (partial)."""

    role_name: str | None = Field(default=None, description="New display name")
    description: str | None = Field(default=None, description="New description")


class DepartmentCreate(BaseModel):
    """Create a new department."""

    name: str = Field(..., description="Department name")
    code: str = Field(..., description="Unique department code")
    parent_id: int | None = Field(default=None, description="Parent department ID (null for top-level)")


class DepartmentResponse(BaseModel):
    """Department information."""

    id: int
    name: str
    code: str
    parent_id: int | None = None
    children_count: int = Field(default=0, description="Number of direct child departments")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Request body to create a new user."""

    username: str = Field(..., description="Login username")
    password: str = Field(..., description="Login password")
    real_name: str = Field(..., description="Real/full name")
    email: str | None = Field(default=None, description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    department_id: int | None = Field(default=None, description="Department ID")
    role_ids: list[int] = Field(default_factory=list, description="List of role IDs to assign")


class UserUpdate(BaseModel):
    """Partial update for an existing user."""

    real_name: str | None = Field(default=None, description="New real name")
    email: str | None = Field(default=None, description="New email")
    phone: str | None = Field(default=None, description="New phone number")
    department_id: int | None = Field(default=None, description="New department ID")
    status: str | None = Field(default=None, description="New status (active/disabled)")


class UserResponse(BaseModel):
    """User information returned in API responses."""

    id: int
    username: str
    real_name: str
    email: str | None = None
    phone: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    avatar_url: str | None = None
    status: str
    roles: list[RoleInfo] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(PaginatedResponse["UserResponse"]):
    """Paginated list of users."""

    pass
