from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.core.pagination import PaginationParams
from app.models.user import User
from app.services.search_service import SearchService

router = APIRouter()
search_service = SearchService()


# ---------- Pydantic Schemas ----------

class SearchResult(BaseModel):
    id: int
    type: str  # "document"
    title: str
    description: str | None
    file_type: str | None
    created_at: str | None
    highlights: dict[str, list[str]] = {}

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    items: list[SearchResult]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------- Helper ----------

async def _build_user_dict(current_user: User, db: AsyncSession) -> dict:
    """Build a current_user dict for service calls from a User model."""
    from app.core.permissions import RoleCode

    role_codes = [r.role_code for r in (current_user.roles or []) if hasattr(r, 'role_code')]
    user_dict = {"id": current_user.id, "roles": role_codes}
    return user_dict


# ---------- Routes ----------

@router.get("/", response_model=SearchResponse)
async def search(
    keyword: str = Query(..., min_length=1),
    file_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_dict = await _build_user_dict(current_user, db)
    pagination = PaginationParams(page=page, page_size=page_size)

    doc_results = await search_service.search_documents(
        db, keyword, file_type, None, pagination, user_dict
    )
    total = doc_results["total"]

    results = []
    for doc in doc_results["items"]:
        results.append(SearchResult(
            id=doc["id"],
            type="document",
            title=doc["title"],
            description=doc["description"],
            file_type=doc["file_type"],
            created_at=doc["created_at"],
        ))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return SearchResponse(
        items=results,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
