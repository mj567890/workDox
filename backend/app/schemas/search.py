from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request parameters."""

    keyword: str = Field(..., description="Search keyword/query")
    scope: str = Field(default="all", description="Search scope: all, documents, matters, tasks")
    file_type: str | None = Field(default=None, description="Filter by file type (only for document scope)")
    matter_id: int | None = Field(default=None, description="Filter by associated matter ID")
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class SearchResultItem(BaseModel):
    """A single search result item (unified across entity types)."""

    id: int = Field(..., description="Entity ID")
    type: str = Field(..., description="Entity type: document, matter, task, etc.")
    title: str = Field(..., description="Display title of the result")
    description: str | None = Field(default=None, description="Snippet or description")
    highlight: str | None = Field(default=None, description="HTML-highlighted text snippet")
    url: str | None = Field(default=None, description="Deep link to the entity detail page")
    extra: dict | None = Field(default=None, description="Additional entity-specific metadata")
