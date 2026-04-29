from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Generic API response wrapper."""

    code: int = Field(default=200, description="HTTP status code")
    message: str = Field(default="success", description="Response message")
    data: T | None = Field(default=None, description="Response payload")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T] = Field(default_factory=list, description="List of items for the current page")
    total: int = Field(default=0, description="Total number of items across all pages")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=20, description="Number of items per page")
    total_pages: int = Field(default=0, description="Total number of pages")


class PaginationParams(BaseModel):
    """Pagination request parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page (max 100)")


class SortParams(BaseModel):
    """Sorting request parameters."""

    sort_by: str | None = Field(default=None, description="Field name to sort by")
    sort_order: str = Field(
        default="desc",
        pattern=r"^(asc|desc)$",
        description="Sort order: asc or desc",
    )
