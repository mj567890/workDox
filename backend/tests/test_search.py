"""Tests for document search service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams


@pytest.fixture
async def seed_search_data(db_session: AsyncSession):
    """Seed documents with varied names and types for search tests."""
    from app.models.user import User
    from app.models.document import Document
    from app.core.security import hash_password

    # Need users for owner_id FK
    admin = User(
        id=1, username="admin", password_hash=hash_password("pw"),
        real_name="管理员", status="active",
    )
    staff = User(
        id=2, username="staff1", password_hash=hash_password("pw"),
        real_name="员工", status="active",
    )
    db_session.add_all([admin, staff])
    await db_session.flush()

    docs = [
        Document(
            original_name="2025年度工作总结报告.pdf",
            file_type="pdf", file_size=1024,
            mime_type="application/pdf",
            storage_path="/docs/report1.pdf",
            owner_id=1, status="draft",
            description="年度工作总结与明年计划",
        ),
        Document(
            original_name="招生工作方案.docx",
            file_type="docx", file_size=2048,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            storage_path="/docs/plan.docx",
            owner_id=1, status="draft",
            description="2026年度招生工作方案",
        ),
        Document(
            original_name="经费预算表.xlsx",
            file_type="xlsx", file_size=512,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            storage_path="/docs/budget.xlsx",
            owner_id=2, status="draft",
            description="年度预算明细",
        ),
        Document(
            original_name="招生简章-final.pdf",
            file_type="pdf", file_size=4096,
            mime_type="application/pdf",
            storage_path="/docs/brochure.pdf",
            owner_id=1, status="draft",
            description=None,
        ),
        Document(
            original_name="已删除的文档.pdf",
            file_type="pdf", file_size=100,
            mime_type="application/pdf",
            storage_path="/docs/deleted.pdf",
            owner_id=1, status="draft",
            is_deleted=True,  # soft-deleted
        ),
    ]
    db_session.add_all(docs)
    await db_session.commit()


# ── Helpers ───────────────────────────────────────────────────────────

def _admin_user():
    return {"id": 1, "roles": ["admin"]}


def _staff_user():
    return {"id": 2, "roles": ["general_staff"]}


# ── Tests ─────────────────────────────────────────────────────────────

class TestSearchService:
    """Test SearchService.search_documents with various filters."""

    async def test_search_by_keyword_short(self, db_session, seed_search_data):
        """Short keyword (<=2 chars) should use ILIKE fallback + FTS."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="招生", file_type=None, matter_id=None,
            pagination=PaginationParams(page=1, page_size=20),
            current_user=_admin_user(),
        )

        assert result["total"] == 2
        titles = [item["title"] for item in result["items"]]
        assert any("招生" in t for t in titles)

    async def test_search_by_keyword_long(self, db_session, seed_search_data):
        """Longer keyword (>2 chars) should use FTS primarily."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="工作总结", file_type=None, matter_id=None,
            pagination=PaginationParams(page=1, page_size=20),
            current_user=_admin_user(),
        )

        assert result["total"] == 1
        assert "2025年度工作总结报告" in result["items"][0]["title"]

    async def test_search_by_keyword_in_description(self, db_session, seed_search_data):
        """Keyword should match description field too (via ILIKE for short keywords)."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="预算", file_type=None, matter_id=None,
            pagination=PaginationParams(page=1, page_size=20),
            current_user=_admin_user(),
        )

        # "预算" appears in description of 经费预算表.xlsx
        assert result["total"] >= 1
        titles = [item["title"] for item in result["items"]]
        assert any("预算" in t for t in titles)

    async def test_search_with_file_type_filter(self, db_session, seed_search_data):
        """Filter by file_type should narrow results."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="", file_type="pdf", matter_id=None,
            pagination=PaginationParams(page=1, page_size=20),
            current_user=_admin_user(),
        )

        # 4 pdf docs total, but 1 is soft-deleted
        assert result["total"] == 3
        for item in result["items"]:
            assert item["file_type"] == "pdf"

    async def test_search_no_results(self, db_session, seed_search_data):
        """Search for a non-existent keyword returns empty."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="ZZZZZ_NONEXISTENT_ZZZZZ", file_type=None,
            matter_id=None,
            pagination=PaginationParams(page=1, page_size=20),
            current_user=_admin_user(),
        )

        assert result["total"] == 0
        assert result["items"] == []

    async def test_soft_deleted_excluded(self, db_session, seed_search_data):
        """Soft-deleted documents should never appear in results."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="已删除", file_type=None, matter_id=None,
            pagination=PaginationParams(page=1, page_size=20),
            current_user=_admin_user(),
        )

        # "已删除的文档" is soft-deleted, so should not appear
        for item in result["items"]:
            assert "已删除" not in item["title"]

    async def test_pagination(self, db_session, seed_search_data):
        """Pagination should limit and offset results correctly."""
        from app.services.search_service import SearchService

        svc = SearchService()

        # Page 1 with 2 per page
        result = await svc.search_documents(
            db_session, keyword="", file_type=None, matter_id=None,
            pagination=PaginationParams(page=1, page_size=2),
            current_user=_admin_user(),
        )

        assert result["total"] == 4  # 4 non-deleted docs
        assert len(result["items"]) == 2

        # Page 2 with 2 per page
        result_p2 = await svc.search_documents(
            db_session, keyword="", file_type=None, matter_id=None,
            pagination=PaginationParams(page=2, page_size=2),
            current_user=_admin_user(),
        )

        assert len(result_p2["items"]) == 2
        # Items should not overlap across pages
        p1_ids = {item["id"] for item in result["items"]}
        p2_ids = {item["id"] for item in result_p2["items"]}
        assert p1_ids.isdisjoint(p2_ids)

    async def test_admin_sees_all_documents(self, db_session, seed_search_data):
        """Admin should see documents owned by any user."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="", file_type=None, matter_id=None,
            pagination=PaginationParams(page=1, page_size=50),
            current_user=_admin_user(),
        )

        assert result["total"] == 4  # All non-deleted docs

    async def test_staff_sees_only_own_documents(self, db_session, seed_search_data):
        """Non-admin staff should only see their own documents."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="", file_type=None, matter_id=None,
            pagination=PaginationParams(page=1, page_size=50),
            current_user=_staff_user(),
        )

        # Staff owns exactly 1 document (经费预算表.xlsx)
        assert result["total"] == 1
        assert result["items"][0]["title"] == "经费预算表.xlsx"

    async def test_keyword_and_type_combined(self, db_session, seed_search_data):
        """Combined keyword + file_type filter."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="招生", file_type="pdf", matter_id=None,
            pagination=PaginationParams(page=1, page_size=20),
            current_user=_admin_user(),
        )

        # Only "招生简章-final.pdf" matches both keyword AND pdf type
        assert result["total"] == 1
        assert result["items"][0]["title"] == "招生简章-final.pdf"

    async def test_empty_keyword_returns_all(self, db_session, seed_search_data):
        """Empty keyword with no other filters should return all non-deleted docs."""
        from app.services.search_service import SearchService

        svc = SearchService()
        result = await svc.search_documents(
            db_session, keyword="", file_type=None, matter_id=None,
            pagination=PaginationParams(page=1, page_size=50),
            current_user=_admin_user(),
        )

        assert result["total"] == 4
        assert len(result["items"]) == 4
