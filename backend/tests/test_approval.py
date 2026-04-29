"""Tests for document approval workflow (DocumentReview)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def seed_approval_data(db_session: AsyncSession):
    """Seed data for approval workflow tests."""
    from app.models.user import User
    from app.models.role import Role
    from app.models.document import Document, DocumentCategory
    from app.core.security import hash_password

    roles = [
        Role(id=1, role_name="管理员", role_code="admin"),
        Role(id=2, role_name="部门领导", role_code="dept_leader"),
        Role(id=3, role_name="事项负责人", role_code="matter_owner"),
    ]
    db_session.add_all(roles)
    await db_session.flush()

    users = {
        "owner": User(id=1, username="owner1", password_hash=hash_password("pw"), real_name="文档所有者", status="active"),
        "reviewer1": User(id=2, username="reviewer1", password_hash=hash_password("pw"), real_name="审批人A", status="active"),
        "reviewer2": User(id=3, username="reviewer2", password_hash=hash_password("pw"), real_name="审批人B", status="active"),
    }
    users["owner"].roles.append(roles[0])
    db_session.add_all(users.values())

    cat = DocumentCategory(id=1, name="通知文件", code="notice")
    db_session.add(cat)

    doc = Document(
        id=1, original_name="待审批.pdf", file_type="pdf", file_size=1024,
        mime_type="application/pdf", storage_path="/tmp/review.pdf",
        owner_id=1, status="draft",
    )
    db_session.add(doc)
    await db_session.commit()


class TestDocumentApproval:
    async def test_submit_for_review(self, db_session, seed_approval_data):
        from app.services.document_service import review_service
        from app.models.document import Document
        from sqlalchemy import select

        doc = await review_service.submit_for_review(
            db_session, doc_id=1, reviewer_ids=[2, 3], current_user_id=1
        )
        assert doc.status == "submitted"

    async def test_multi_level_approval(self, db_session, seed_approval_data):
        from app.services.document_service import review_service
        from app.models.document import Document
        from sqlalchemy import select

        # Submit with 2 reviewers
        await review_service.submit_for_review(
            db_session, doc_id=1, reviewer_ids=[2, 3], current_user_id=1
        )

        # Level 1 approves
        review1 = await review_service.approve_document(
            db_session, doc_id=1, review_level=1, reviewer_id=2, comment="初审通过"
        )
        assert review1.status == "approved"

        # After level 1 only, document should be "reviewing"
        stmt = select(Document).where(Document.id == 1)
        r = await db_session.execute(stmt)
        doc = r.scalars().first()
        assert doc.status == "reviewing"

        # Level 2 approves
        review2 = await review_service.approve_document(
            db_session, doc_id=1, review_level=2, reviewer_id=3, comment="终审通过"
        )
        assert review2.status == "approved"

        # After all approved, document should be "approved"
        await db_session.refresh(doc)
        assert doc.status == "approved"

    async def test_reject_document(self, db_session, seed_approval_data):
        from app.services.document_service import review_service
        from app.models.document import Document
        from sqlalchemy import select

        await review_service.submit_for_review(
            db_session, doc_id=1, reviewer_ids=[2, 3], current_user_id=1
        )

        review = await review_service.reject_document(
            db_session, doc_id=1, review_level=1, reviewer_id=2, comment="需要修改"
        )
        assert review.status == "rejected"

        stmt = select(Document).where(Document.id == 1)
        r = await db_session.execute(stmt)
        doc = r.scalars().first()
        assert doc.status == "rejected"

    async def test_wrong_reviewer_cannot_approve(self, db_session, seed_approval_data):
        from app.services.document_service import review_service
        from app.core.exceptions import ForbiddenException

        await review_service.submit_for_review(
            db_session, doc_id=1, reviewer_ids=[2, 3], current_user_id=1
        )

        # User 3 tries to approve level 1 (should be user 2)
        with pytest.raises(ForbiddenException):
            await review_service.approve_document(
                db_session, doc_id=1, review_level=1, reviewer_id=3
            )

    async def test_cannot_submit_if_not_owner(self, db_session, seed_approval_data):
        from app.services.document_service import review_service
        from app.core.exceptions import ForbiddenException

        with pytest.raises(ForbiddenException):
            await review_service.submit_for_review(
                db_session, doc_id=1, reviewer_ids=[2], current_user_id=999
            )

    async def test_get_pending_reviews(self, db_session, seed_approval_data):
        from app.services.document_service import review_service

        await review_service.submit_for_review(
            db_session, doc_id=1, reviewer_ids=[2, 3], current_user_id=1
        )

        # User 2 has 1 pending review
        pending = await review_service.get_pending_reviews_for_user(db_session, user_id=2)
        assert len(pending) == 1
        assert pending[0].review_level == 1

        # User 4 has no pending reviews
        no_pending = await review_service.get_pending_reviews_for_user(db_session, user_id=999)
        assert len(no_pending) == 0

    async def test_submit_without_reviewers(self, db_session, seed_approval_data):
        from app.services.document_service import review_service
        from app.core.exceptions import ValidationException

        with pytest.raises(ValidationException):
            await review_service.submit_for_review(
                db_session, doc_id=1, reviewer_ids=[], current_user_id=1
            )
