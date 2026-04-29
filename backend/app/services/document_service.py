from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import (
    Document,
    DocumentVersion,
    DocumentCategory,
    Tag,
    DocumentEditLock,
    DocumentReview,
    CrossMatterReference,
)
from app.models.matter import Matter, MatterMember
from app.core.pagination import PaginationParams
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ConflictException,
    ValidationException,
    DocumentLockedException,
    VersionConflictException,
)
from app.core.permissions import RoleCode


class DocumentService:

    async def get_documents(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        filters: dict,
        current_user: dict,
    ) -> tuple[list[Document], int]:
        conditions = [Document.is_deleted == False]
        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])

        if filters.get("matter_id"):
            if "admin" not in user_roles:
                member_result = await db.execute(
                    select(MatterMember).where(
                        MatterMember.matter_id == filters["matter_id"],
                        MatterMember.user_id == user_id,
                    )
                )
                if not member_result.scalars().first():
                    raise ForbiddenException(
                        detail="You are not a member of this matter"
                    )
            conditions.append(Document.matter_id == filters["matter_id"])
        if filters.get("category_id"):
            conditions.append(Document.category_id == filters["category_id"])
        if filters.get("tag_id"):
            conditions.append(
                Document.id.in_(
                    select(Document.id)
                    .join(Document.tags)
                    .where(Tag.id == filters["tag_id"])
                )
            )
        if filters.get("status"):
            conditions.append(Document.status == filters["status"])
        if filters.get("file_type"):
            conditions.append(Document.file_type == filters["file_type"])
        if filters.get("keyword"):
            kw = f"%{filters['keyword']}%"
            conditions.append(
                or_(
                    Document.original_name.ilike(kw),
                    Document.description.ilike(kw),
                )
            )

        base_query = (
            select(Document)
            .options(
                selectinload(Document.owner),
                selectinload(Document.category),
                selectinload(Document.tags),
                selectinload(Document.current_version),
            )
            .where(and_(*conditions))
        )

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(Document.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def get_document(
        self,
        db: AsyncSession,
        doc_id: int,
        current_user: dict,
    ) -> Document:
        stmt = (
            select(Document)
            .options(
                selectinload(Document.owner),
                selectinload(Document.category),
                selectinload(Document.tags),
                selectinload(Document.current_version),
                selectinload(Document.versions),
                selectinload(Document.edit_lock),
                selectinload(Document.reviews).selectinload(DocumentReview.reviewer),
                selectinload(Document.cross_references),
                selectinload(Document.matter),
            )
            .where(Document.id == doc_id, Document.is_deleted == False)
        )
        result = await db.execute(stmt)
        document = result.scalars().first()

        if not document:
            raise NotFoundException(resource="Document")

        await self._check_document_access(document, current_user)
        return document

    async def create_document(
        self,
        db: AsyncSession,
        data: "DocumentCreate",
        file_info: dict,
        user_id: int,
    ) -> Document:
        document = Document(
            original_name=file_info["original_name"],
            file_type=file_info["file_type"],
            file_size=file_info["file_size"],
            mime_type=file_info["mime_type"],
            storage_path=file_info["storage_path"],
            description=data.description,
            owner_id=user_id,
            matter_id=data.matter_id,
            category_id=data.category_id,
            status="draft",
            permission_scope=getattr(data, "permission_scope", "matter"),
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        if data.tag_ids:
            await self._assign_tags(db, document, data.tag_ids)

        return document

    async def update_document(
        self,
        db: AsyncSession,
        doc_id: int,
        data: "DocumentUpdate",
        current_user: dict,
    ) -> Document:
        document = await self.get_document(db, doc_id, current_user)

        if document.owner_id != current_user.get("id") and "admin" not in current_user.get("roles", []):
            raise ForbiddenException(detail="Only the document owner or admin can update this document")

        update_data = data.model_dump(exclude_unset=True)

        if "tag_ids" in update_data:
            tag_ids = update_data.pop("tag_ids")
            await self._assign_tags(db, document, tag_ids)

        for key, value in update_data.items():
            if hasattr(document, key) and key not in ("id", "storage_path"):
                setattr(document, key, value)

        await db.commit()
        await db.refresh(document)
        return document

    async def soft_delete_document(
        self,
        db: AsyncSession,
        doc_id: int,
        current_user: dict,
    ) -> bool:
        document = await self.get_document(db, doc_id, current_user)

        if document.owner_id != current_user.get("id") and "admin" not in current_user.get("roles", []):
            raise ForbiddenException(detail="Only the document owner or admin can delete this document")

        document.is_deleted = True
        await db.commit()
        return True

    async def get_document_categories(
        self, db: AsyncSession
    ) -> list[DocumentCategory]:
        stmt = select(DocumentCategory).order_by(DocumentCategory.sort_order, DocumentCategory.id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_category(
        self, db: AsyncSession, data: "DocumentCategoryCreate"
    ) -> DocumentCategory:
        existing = await db.execute(
            select(DocumentCategory).where(DocumentCategory.code == data.code)
        )
        if existing.scalars().first():
            raise ConflictException(
                detail=f"Category code '{data.code}' already exists"
            )

        category = DocumentCategory(
            name=data.name,
            code=data.code,
            description=data.description,
            sort_order=data.sort_order if hasattr(data, "sort_order") else 0,
            is_system=data.is_system if hasattr(data, "is_system") else False,
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    async def update_category(
        self, db: AsyncSession, cat_id: int, data: "DocumentCategoryUpdate"
    ) -> DocumentCategory:
        result = await db.execute(
            select(DocumentCategory).where(DocumentCategory.id == cat_id)
        )
        category = result.scalars().first()
        if not category:
            raise NotFoundException(resource="DocumentCategory")

        update_data = data.model_dump(exclude_unset=True)

        if "code" in update_data:
            existing = await db.execute(
                select(DocumentCategory).where(
                    DocumentCategory.code == update_data["code"],
                    DocumentCategory.id != cat_id,
                )
            )
            if existing.scalars().first():
                raise ConflictException(
                    detail=f"Category code '{update_data['code']}' already exists"
                )

        for key, value in update_data.items():
            if hasattr(category, key) and key != "id":
                setattr(category, key, value)

        await db.commit()
        await db.refresh(category)
        return category

    async def delete_category(self, db: AsyncSession, cat_id: int) -> bool:
        result = await db.execute(
            select(DocumentCategory).where(DocumentCategory.id == cat_id)
        )
        category = result.scalars().first()
        if not category:
            raise NotFoundException(resource="DocumentCategory")

        doc_result = await db.execute(
            select(func.count()).where(Document.category_id == cat_id)
        )
        if doc_result.scalar() > 0:
            raise ConflictException(
                detail="Cannot delete category with existing documents"
            )

        await db.delete(category)
        await db.commit()
        return True

    async def get_tags(self, db: AsyncSession) -> list[Tag]:
        stmt = select(Tag).order_by(Tag.id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_tag(self, db: AsyncSession, data: "TagCreate") -> Tag:
        existing = await db.execute(
            select(Tag).where(Tag.name == data.name)
        )
        if existing.scalars().first():
            raise ConflictException(
                detail=f"Tag '{data.name}' already exists"
            )

        tag = Tag(
            name=data.name,
            color=data.color if hasattr(data, "color") else "#409EFF",
        )
        db.add(tag)
        await db.commit()
        await db.refresh(tag)
        return tag

    async def delete_tag(self, db: AsyncSession, tag_id: int) -> bool:
        result = await db.execute(select(Tag).where(Tag.id == tag_id))
        tag = result.scalars().first()
        if not tag:
            raise NotFoundException(resource="Tag")

        await db.delete(tag)
        await db.commit()
        return True

    async def _check_document_access(
        self, document: Document, current_user: dict
    ) -> None:
        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])

        if "admin" in user_roles:
            return

        if document.owner_id == user_id:
            return

        if document.matter_id:
            member_result = await db.session.get(
                select(MatterMember).where(
                    MatterMember.matter_id == document.matter_id,
                    MatterMember.user_id == user_id,
                )
            )
            # Note: This needs db access - adjust pattern

    async def _check_document_access_with_db(
        self, db: AsyncSession, document: Document, current_user: dict
    ) -> None:
        user_id = current_user.get("id")
        user_roles: list[str] = current_user.get("roles", [])

        if "admin" in user_roles:
            return

        if document.owner_id == user_id:
            return

        if document.matter_id:
            member_result = await db.execute(
                select(MatterMember).where(
                    MatterMember.matter_id == document.matter_id,
                    MatterMember.user_id == user_id,
                )
            )
            if member_result.scalars().first():
                return

        ref_result = await db.execute(
            select(CrossMatterReference).where(
                CrossMatterReference.document_id == document.id
            )
        )
        if ref_result.scalars().first():
            return

        raise ForbiddenException(
            detail="You do not have permission to access this document"
        )

    async def _assign_tags(
        self, db: AsyncSession, document: Document, tag_ids: list[int]
    ) -> None:
        tags_result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        tags = tags_result.scalars().all()

        if len(tags) != len(tag_ids):
            found_ids = {tag.id for tag in tags}
            missing = set(tag_ids) - found_ids
            raise NotFoundException(resource=f"Tag(s): {missing}")

        document.tags = list(tags)
        await db.commit()


class DocumentVersionService:

    async def get_versions(
        self, db: AsyncSession, doc_id: int
    ) -> list[DocumentVersion]:
        stmt = (
            select(DocumentVersion)
            .options(selectinload(DocumentVersion.upload_user))
            .where(DocumentVersion.document_id == doc_id)
            .order_by(DocumentVersion.version_no.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def upload_new_version(
        self,
        db: AsyncSession,
        doc_id: int,
        file_info: dict,
        user_id: int,
        change_note: str | None,
        set_as_official: bool = False,
    ) -> DocumentVersion:
        doc_result = await db.execute(
            select(Document).where(Document.id == doc_id, Document.is_deleted == False)
        )
        document = doc_result.scalars().first()
        if not document:
            raise NotFoundException(resource="Document")

        max_version_result = await db.execute(
            select(func.max(DocumentVersion.version_no)).where(
                DocumentVersion.document_id == doc_id
            )
        )
        max_version = max_version_result.scalar() or 0
        new_version_no = max_version + 1

        if set_as_oficial:
            await db.execute(
                update(DocumentVersion)
                .where(DocumentVersion.document_id == doc_id)
                .values(is_official=False)
            )

        version = DocumentVersion(
            document_id=doc_id,
            version_no=new_version_no,
            file_path=file_info["storage_path"],
            file_size=file_info["file_size"],
            upload_user_id=user_id,
            change_note=change_note,
            is_official=set_as_official,
            checksum=file_info.get("checksum"),
        )
        db.add(version)
        await db.flush()

        if set_as_oficial:
            document.current_version_id = version.id
            document.status = "official"
            document.storage_path = file_info["storage_path"]
            document.file_size = file_info["file_size"]
            document.file_type = file_info.get("file_type", document.file_type)
            document.mime_type = file_info.get("mime_type", document.mime_type)

        await db.commit()
        await db.refresh(version)
        return version

    async def set_official_version(
        self,
        db: AsyncSession,
        doc_id: int,
        version_id: int,
        current_user: dict,
    ) -> DocumentVersion:
        user_roles: list[str] = current_user.get("roles", [])
        has_official_perm = any(
            role in ["admin", "dept_leader", "matter_owner"]
            for role in user_roles
        )
        if not has_official_perm:
            raise ForbiddenException(
                detail="Only admin, dept_leader, or matter_owner can set official version"
            )

        doc_result = await db.execute(
            select(Document).where(Document.id == doc_id, Document.is_deleted == False)
        )
        document = doc_result.scalars().first()
        if not document:
            raise NotFoundException(resource="Document")

        ver_result = await db.execute(
            select(DocumentVersion).where(
                DocumentVersion.id == version_id,
                DocumentVersion.document_id == doc_id,
            )
        )
        version = ver_result.scalars().first()
        if not version:
            raise NotFoundException(resource="DocumentVersion")

        await db.execute(
            update(DocumentVersion)
            .where(DocumentVersion.document_id == doc_id)
            .values(is_official=False)
        )

        version.is_official = True
        document.current_version_id = version.id
        document.status = "official"
        document.storage_path = version.file_path
        document.file_size = version.file_size

        await db.commit()
        await db.refresh(version)
        return version

    async def check_version_conflict(
        self, db: AsyncSession, doc_id: int, known_version_no: int
    ) -> bool:
        max_version_result = await db.execute(
            select(func.max(DocumentVersion.version_no)).where(
                DocumentVersion.document_id == doc_id
            )
        )
        max_version = max_version_result.scalar() or 0
        return max_version > known_version_no


class DocumentLockService:

    async def lock_document(
        self, db: AsyncSession, doc_id: int, user_id: int
    ) -> DocumentEditLock:
        doc_result = await db.execute(
            select(Document).where(Document.id == doc_id, Document.is_deleted == False)
        )
        document = doc_result.scalars().first()
        if not document:
            raise NotFoundException(resource="Document")

        existing_lock_result = await db.execute(
            select(DocumentEditLock).where(
                DocumentEditLock.document_id == doc_id,
                DocumentEditLock.expires_at > datetime.now(timezone.utc),
            )
        )
        existing_lock = existing_lock_result.scalars().first()
        if existing_lock:
            if existing_lock.locked_by != user_id:
                locker_result = await db.execute(
                    select(DocumentEditLock)
                    .options(selectinload(DocumentEditLock.locker))
                    .where(DocumentEditLock.id == existing_lock.id)
                )
                lock_info = locker_result.scalars().first()
                locker_name = lock_info.locker.real_name if lock_info and lock_info.locker else "another user"
                raise DocumentLockedException(locked_by=locker_name)
            else:
                existing_lock.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
                await db.commit()
                await db.refresh(existing_lock)
                return existing_lock

        lock = DocumentEditLock(
            document_id=doc_id,
            locked_by=user_id,
            locked_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(lock)
        await db.commit()
        await db.refresh(lock)
        return lock

    async def unlock_document(
        self, db: AsyncSession, doc_id: int, user_id: int
    ) -> bool:
        lock_result = await db.execute(
            select(DocumentEditLock).where(DocumentEditLock.document_id == doc_id)
        )
        lock = lock_result.scalars().first()

        if not lock:
            return True

        user_roles: list[str] = []
        user_result = await db.execute(
            select(DocumentEditLock).where(
                DocumentEditLock.document_id == doc_id,
                DocumentEditLock.locked_by == user_id,
            )
        )
        is_holder = user_result.scalars().first() is not None

        if not is_holder:
            raise ForbiddenException(
                detail="Only the lock holder or admin can unlock this document"
            )

        await db.delete(lock)
        await db.commit()
        return True

    async def get_lock_status(
        self, db: AsyncSession, doc_id: int
    ) -> dict:
        lock_result = await db.execute(
            select(DocumentEditLock)
            .options(selectinload(DocumentEditLock.locker))
            .where(DocumentEditLock.document_id == doc_id)
        )
        lock = lock_result.scalars().first()

        if not lock or lock.expires_at < datetime.now(timezone.utc):
            return {"is_locked": False, "locked_by": None, "expires_at": None}

        return {
            "is_locked": True,
            "locked_by": {
                "id": lock.locker.id,
                "real_name": lock.locker.real_name,
                "username": lock.locker.username,
            },
            "locked_at": lock.locked_at.isoformat(),
            "expires_at": lock.expires_at.isoformat(),
        }

    async def check_and_release_expired_locks(
        self, db: AsyncSession
    ) -> int:
        result = await db.execute(
            delete(DocumentEditLock).where(
                DocumentEditLock.expires_at < datetime.now(timezone.utc)
            )
        )
        await db.commit()
        return result.rowcount


class CrossReferenceService:

    async def add_reference(
        self,
        db: AsyncSession,
        doc_id: int,
        matter_id: int,
        user_id: int,
        is_readonly: bool = True,
    ) -> CrossMatterReference:
        doc_result = await db.execute(
            select(Document).where(Document.id == doc_id, Document.is_deleted == False)
        )
        document = doc_result.scalars().first()
        if not document:
            raise NotFoundException(resource="Document")

        matter_result = await db.execute(
            select(Matter).where(Matter.id == matter_id)
        )
        matter = matter_result.scalars().first()
        if not matter:
            raise NotFoundException(resource="Matter")

        existing = await db.execute(
            select(CrossMatterReference).where(
                CrossMatterReference.document_id == doc_id,
                CrossMatterReference.matter_id == matter_id,
            )
        )
        if existing.scalars().first():
            raise ConflictException(
                detail="This document is already referenced in this matter"
            )

        ref = CrossMatterReference(
            document_id=doc_id,
            matter_id=matter_id,
            is_readonly=is_readonly,
            added_by=user_id,
        )
        db.add(ref)
        await db.commit()
        await db.refresh(ref)
        return ref

    async def remove_reference(
        self, db: AsyncSession, ref_id: int, user_id: int
    ) -> bool:
        result = await db.execute(
            select(CrossMatterReference).where(CrossMatterReference.id == ref_id)
        )
        ref = result.scalars().first()
        if not ref:
            raise NotFoundException(resource="CrossMatterReference")

        await db.delete(ref)
        await db.commit()
        return True

    async def get_references(
        self, db: AsyncSession, doc_id: int
    ) -> list[CrossMatterReference]:
        stmt = (
            select(CrossMatterReference)
            .options(
                selectinload(CrossMatterReference.matter),
                selectinload(CrossMatterReference.adder),
            )
            .where(CrossMatterReference.document_id == doc_id)
            .order_by(CrossMatterReference.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


class DocumentReviewService:

    async def submit_for_review(
        self,
        db: AsyncSession,
        doc_id: int,
        reviewer_ids: list[int],
        current_user_id: int,
    ) -> Document:
        """Submit a document for approval with specified reviewers."""
        doc_result = await db.execute(
            select(Document)
            .options(selectinload(Document.owner))
            .where(Document.id == doc_id, Document.is_deleted == False)
        )
        document = doc_result.scalars().first()
        if not document:
            raise NotFoundException(resource="Document")

        if document.owner_id != current_user_id:
            raise ForbiddenException(detail="Only the document owner can submit for review")

        if document.status not in ("draft", "rejected"):
            raise ValidationException(
                detail=f"Cannot submit document in '{document.status}' status"
            )

        if not reviewer_ids:
            raise ValidationException(detail="At least one reviewer is required")

        # Verify all reviewers exist
        from app.models.user import User
        users_result = await db.execute(
            select(User).where(User.id.in_(reviewer_ids))
        )
        users = users_result.scalars().all()
        if len(users) != len(reviewer_ids):
            raise ValidationException(detail="One or more reviewers not found")

        # Remove any existing pending reviews
        existing = await db.execute(
            select(DocumentReview).where(
                DocumentReview.document_id == doc_id,
                DocumentReview.status == "pending",
            )
        )
        for review in existing.scalars().all():
            await db.delete(review)
        await db.flush()

        # Create review records for each level
        for i, reviewer_id in enumerate(reviewer_ids):
            review = DocumentReview(
                document_id=doc_id,
                review_level=i + 1,
                reviewer_id=reviewer_id,
                status="pending",
            )
            db.add(review)

        # Update document status
        document.status = "submitted"
        document.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(document)
        return document

    async def approve_document(
        self,
        db: AsyncSession,
        doc_id: int,
        review_level: int,
        reviewer_id: int,
        comment: str | None = None,
    ) -> DocumentReview:
        """Approve a document at the given review level."""
        review_result = await db.execute(
            select(DocumentReview).where(
                DocumentReview.document_id == doc_id,
                DocumentReview.review_level == review_level,
            )
        )
        review = review_result.scalars().first()
        if not review:
            raise NotFoundException(resource="DocumentReview")

        if review.reviewer_id != reviewer_id:
            raise ForbiddenException(detail="You are not the designated reviewer for this level")

        if review.status != "pending":
            raise ValidationException(detail=f"Review already {review.status}")

        review.status = "approved"
        review.comment = comment
        review.reviewed_at = datetime.now(timezone.utc)

        # Check if all reviews are approved
        all_reviews_result = await db.execute(
            select(DocumentReview).where(
                DocumentReview.document_id == doc_id,
            ).order_by(DocumentReview.review_level)
        )
        all_reviews = all_reviews_result.scalars().all()

        all_approved = all(r.status == "approved" for r in all_reviews)
        if all_approved:
            doc_result = await db.execute(
                select(Document).where(Document.id == doc_id)
            )
            document = doc_result.scalars().first()
            if document:
                document.status = "approved"
                document.updated_at = datetime.now(timezone.utc)
        else:
            # Update to reviewing if not all done yet
            doc_result = await db.execute(
                select(Document).where(Document.id == doc_id)
            )
            document = doc_result.scalars().first()
            if document and document.status != "reviewing":
                document.status = "reviewing"
                document.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(review)
        return review

    async def reject_document(
        self,
        db: AsyncSession,
        doc_id: int,
        review_level: int,
        reviewer_id: int,
        comment: str | None = None,
    ) -> DocumentReview:
        """Reject a document at the given review level."""
        review_result = await db.execute(
            select(DocumentReview).where(
                DocumentReview.document_id == doc_id,
                DocumentReview.review_level == review_level,
            )
        )
        review = review_result.scalars().first()
        if not review:
            raise NotFoundException(resource="DocumentReview")

        if review.reviewer_id != reviewer_id:
            raise ForbiddenException(detail="You are not the designated reviewer for this level")

        if review.status != "pending":
            raise ValidationException(detail=f"Review already {review.status}")

        review.status = "rejected"
        review.comment = comment
        review.reviewed_at = datetime.now(timezone.utc)

        # Update document status to rejected
        doc_result = await db.execute(
            select(Document).where(Document.id == doc_id)
        )
        document = doc_result.scalars().first()
        if document:
            document.status = "rejected"
            document.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(review)
        return review

    async def get_reviews(
        self, db: AsyncSession, doc_id: int
    ) -> list[DocumentReview]:
        """Get all reviews for a document ordered by review level."""
        stmt = (
            select(DocumentReview)
            .options(selectinload(DocumentReview.reviewer))
            .where(DocumentReview.document_id == doc_id)
            .order_by(DocumentReview.review_level)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_reviews_for_user(
        self, db: AsyncSession, user_id: int
    ) -> list[DocumentReview]:
        """Get all pending reviews assigned to a user."""
        stmt = (
            select(DocumentReview)
            .options(
                selectinload(DocumentReview.reviewer),
                selectinload(DocumentReview.document).selectinload(Document.owner),
            )
            .where(
                DocumentReview.reviewer_id == user_id,
                DocumentReview.status == "pending",
            )
            .order_by(DocumentReview.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


document_service = DocumentService()
version_service = DocumentVersionService()
lock_service = DocumentLockService()
reference_service = CrossReferenceService()
review_service = DocumentReviewService()
