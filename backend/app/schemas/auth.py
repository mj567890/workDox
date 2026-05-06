from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Login credentials request."""

    username: str = Field(..., min_length=2, max_length=64, description="Username")
    password: str = Field(..., min_length=4, max_length=128, description="Password")


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserInfo(BaseModel):
    """Current authenticated user information."""

    id: int
    username: str
    real_name: str
    email: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    roles: list[RoleInfo] = Field(default_factory=list)
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password (min 6 characters)")


# Import at bottom to avoid circular imports
from app.schemas.user import RoleInfo  # noqa: E402, F811
