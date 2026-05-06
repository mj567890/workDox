from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


class TagResponse(BaseModel):
    """Tag information."""

    id: int
    name: str
    color: str

    model_config = ConfigDict(from_attributes=True)


class TagCreate(BaseModel):
    """Create a new tag."""

    name: str = Field(..., min_length=1, max_length=50, description="Tag name")
    color: str = Field(default="#409EFF", max_length=20, description="Tag color (hex code)")


class CategoryResponse(BaseModel):
    """Document category information."""

    id: int
    name: str
    code: str
    description: str | None = None
    sort_order: int = 0
    is_system: bool = False
    document_count: int = Field(default=0, description="Number of documents in this category")

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    """Create a new document category."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    code: str = Field(..., min_length=1, max_length=50, description="Unique category code")
    description: str | None = Field(default=None, max_length=500, description="Optional description")
    sort_order: int = Field(default=0, description="Sort order (lower = first)")


class CategoryUpdate(BaseModel):
    """Update an existing document category (partial)."""

    name: str | None = Field(default=None, max_length=100, description="New category name")
    description: str | None = Field(default=None, max_length=500, description="New description")
    sort_order: int | None = Field(default=None, description="New sort order")


class DocumentVersionResponse(BaseModel):
    """Document version information."""

    id: int
    document_id: int
    version_no: int
    file_size: int
    upload_user_id: int
    upload_user_name: str
    change_note: str | None = None
    is_official: bool = False
    checksum: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VersionUploadRequest(BaseModel):
    """Upload a new version of an existing document."""

    change_note: str | None = Field(default=None, description="Description of changes in this version")
    set_as_official: bool = Field(default=False, description="Set this version as the official one")


class LockResponse(BaseModel):
    """Document edit lock status."""

    locked: bool = Field(..., description="Whether the document is currently locked")
    locked_by: str | None = Field(default=None, description="Name of the user who locked the document")
    locked_at: datetime | None = Field(default=None, description="Time when the lock was acquired")
    expires_at: datetime | None = Field(default=None, description="Time when the lock expires")

    model_config = ConfigDict(from_attributes=True)


class CrossReferenceCreate(BaseModel):
    """Create a cross-matter reference for a document."""

    matter_id: int = Field(..., description="Target matter ID to reference this document in")
    is_readonly: bool = Field(default=True, description="Whether the referenced copy is read-only")


class ChunkUploadInit(BaseModel):
    """Initialize a chunked upload session."""

    original_name: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="Total file size in bytes")
    matter_id: int | None = Field(default=None, description="Associated matter ID")
    category_id: int | None = Field(default=None, description="Document category ID")
    chunk_size: int = Field(..., description="Size of each chunk in bytes")
    total_chunks: int = Field(..., description="Total number of chunks")


class ChunkUploadResponse(BaseModel):
    """Response after receiving a chunk."""

    upload_id: str = Field(..., description="Unique upload session identifier")
    chunk_index: int = Field(..., description="Index of the chunk just received (0-based)")
    completed: bool = Field(..., description="Whether the entire file upload is complete")


class DocumentCreate(BaseModel):
    """Create a new document (metadata only; file uploaded separately)."""

    original_name: str = Field(..., description="Original filename")
    matter_id: int | None = Field(default=None, description="Associated matter ID")
    category_id: int | None = Field(default=None, description="Document category ID")
    description: str | None = Field(default=None, description="Optional document description")
    tag_ids: list[int] = Field(default_factory=list, description="List of tag IDs to assign")


class DocumentUpdate(BaseModel):
    """Partial update for an existing document."""

    original_name: str | None = Field(default=None, description="New filename")
    category_id: int | None = Field(default=None, description="New category ID")
    description: str | None = Field(default=None, description="New description")
    tag_ids: list[int] | None = Field(default=None, description="New list of tag IDs")
    status: str | None = Field(default=None, description="New status (draft/published/archived)")


class DocumentResponse(BaseModel):
    """Document information returned in API responses."""

    id: int
    original_name: str
    file_type: str
    file_size: int
    mime_type: str
    description: str | None = None
    owner_id: int
    owner_name: str
    matter_id: int | None = None
    matter_title: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    status: str
    current_version_id: int | None = None
    current_version_no: int | None = None
    permission_scope: str
    tags: list[TagResponse] = Field(default_factory=list)
    is_locked: bool = Field(default=False, description="Whether the document is currently locked for editing")
    locked_by_name: str | None = Field(default=None, description="Name of the user holding the lock")
    preview_pdf_path: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(PaginatedResponse["DocumentResponse"]):
    """Paginated list of documents."""

    pass


class DocumentFilter(BaseModel):
    """Filter parameters for document listing."""

    matter_id: int | None = Field(default=None, description="Filter by associated matter")
    category_id: int | None = Field(default=None, description="Filter by document category")
    tag_id: int | None = Field(default=None, description="Filter by tag")
    status: str | None = Field(default=None, description="Filter by document status")
    file_type: str | None = Field(default=None, description="Filter by file type/extension")
    keyword: str | None = Field(default=None, description="Full-text search keyword")
