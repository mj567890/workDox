from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_current_user, get_db
from app.core.pagination import PaginationParams
from app.models.user import User
from app.models.matter import Matter, MatterMember
from app.services.search_service import SearchService

router = APIRouter()
search_service = SearchService()


# ---------- Pydantic Schemas ----------

class SearchResult(BaseModel):
    id: int
    type: str  # "document" or "matter"
    title: str
    description: str | None
    file_type: str | None
    matter_id: int | None
    matter_title: str | None
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

    if RoleCode.ADMIN not in role_codes and RoleCode.DEPT_LEADER not in role_codes:
        member_result = await db.execute(
            select(MatterMember.matter_id).where(
                MatterMember.user_id == current_user.id
            )
        )
        member_matter_ids = [row[0] for row in member_result.all()]
        member_matter_ids.append(-1)  # sentinel
        user_dict["accessible_matter_ids"] = member_matter_ids

    return user_dict


async def _resolve_matter_titles(db: AsyncSession, matter_ids: set[int]) -> dict[int, str]:
    """Batch-resolve matter titles for a set of matter IDs."""
    if not matter_ids:
        return {}
    result = await db.execute(
        select(Matter.id, Matter.title).where(Matter.id.in_(matter_ids))
    )
    return {row[0]: row[1] for row in result.all()}


# ---------- Routes ----------

@router.get("/", response_model=SearchResponse)
async def search(
    keyword: str = Query(..., min_length=1),
    scope: str = Query("all"),  # all, documents, matters
    file_type: str = Query(None),
    matter_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_dict = await _build_user_dict(current_user, db)
    combined_results: list[SearchResult] = []
    total_docs = 0
    total_matters = 0

    if scope in ("all", "documents"):
        doc_limit = page_size if scope == "documents" else min(page_size // 2, page_size)
        doc_offset = (page - 1) * page_size if scope == "documents" else 0
        fake_page = doc_offset // doc_limit + 1 if doc_limit > 0 else 1
        doc_pagination = PaginationParams(page=fake_page, page_size=doc_limit)

        doc_results = await search_service.search_documents(
            db, keyword, file_type, matter_id, doc_pagination, user_dict
        )
        total_docs = doc_results["total"]

        # Batch resolve matter titles for all document results
        doc_matter_ids = {d["matter_id"] for d in doc_results["items"] if d["matter_id"]}
        matter_titles = await _resolve_matter_titles(db, doc_matter_ids)

        for doc in doc_results["items"]:
            combined_results.append(SearchResult(
                id=doc["id"],
                type="document",
                title=doc["title"],
                description=doc["description"],
                file_type=doc["file_type"],
                matter_id=doc["matter_id"],
                matter_title=matter_titles.get(doc["matter_id"]) if doc["matter_id"] else None,
                created_at=doc["created_at"],
            ))

    if scope in ("all", "matters"):
        matter_limit = page_size if scope == "matters" else min(page_size // 2, page_size)
        matter_offset = (page - 1) * page_size if scope == "matters" else 0
        fake_page = matter_offset // matter_limit + 1 if matter_limit > 0 else 1
        matter_pagination = PaginationParams(page=fake_page, page_size=matter_limit)

        matter_results = await search_service.search_matters(
            db, keyword, matter_pagination, user_dict
        )
        total_matters = matter_results["total"]

        for matter in matter_results["items"]:
            combined_results.append(SearchResult(
                id=matter["id"],
                type="matter",
                title=matter["title"],
                description=matter["description"],
                file_type=None,
                matter_id=matter["id"],
                matter_title=matter["title"],
                created_at=matter["created_at"],
            ))

    total = total_docs + total_matters

    # Sort combined results by created_at descending
    combined_results.sort(
        key=lambda x: x.created_at or "",
        reverse=True,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return SearchResponse(
        items=combined_results[:page_size],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
