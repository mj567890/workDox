from sqlalchemy import String, Boolean, Integer, DateTime, Text, ForeignKey, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from datetime import datetime
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TimestampMixin


class MatterType(Base, TimestampMixin):
    __tablename__ = "matter_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))

    matters: Mapped[list["Matter"]] = relationship("Matter", back_populates="matter_type_obj")
    workflow_templates: Mapped[list["WorkflowTemplate"]] = relationship("WorkflowTemplate", back_populates="matter_type_obj")


class DocumentCategory(Base, TimestampMixin):
    __tablename__ = "document_category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="category")


class Tag(Base, TimestampMixin):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#409EFF")

    documents: Mapped[list["Document"]] = relationship("Document", secondary="document_tag", back_populates="tags")


class Document(Base, TimestampMixin):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    matter_id: Mapped[int | None] = mapped_column(ForeignKey("matter.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("document_category.id"))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    current_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    permission_scope: Mapped[str] = mapped_column(String(30), default="matter")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    preview_pdf_path: Mapped[str | None] = mapped_column(String(500))
    preview_html_path: Mapped[str | None] = mapped_column(String(500))
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(768), nullable=True)

    owner = relationship("User")
    matter = relationship("Matter", back_populates="documents")
    category = relationship("DocumentCategory", back_populates="documents")
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary="document_tag", back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_no.desc()")
    current_version: Mapped["DocumentVersion | None"] = relationship(
        "DocumentVersion",
        primaryjoin="and_(foreign(Document.current_version_id) == DocumentVersion.id)",
        post_update=True,
    )
    edit_lock = relationship("DocumentEditLock", back_populates="document", uselist=False)
    reviews: Mapped[list["DocumentReview"]] = relationship("DocumentReview", back_populates="document", order_by="DocumentReview.review_level")
    cross_references: Mapped[list["CrossMatterReference"]] = relationship("CrossMatterReference", back_populates="document")
    chunks: Mapped[list["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", order_by="DocumentChunk.chunk_index")

    __table_args__ = (
        Index("idx_document_search",
              text("to_tsvector('simple', coalesce(original_name,'') || ' ' || coalesce(description,''))"),
              postgresql_using="gin"),
    )


class DocumentVersion(Base, TimestampMixin):
    __tablename__ = "document_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    upload_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    change_note: Mapped[str | None] = mapped_column(String(1000))
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    checksum: Mapped[str | None] = mapped_column(String(64))

    document = relationship("Document", back_populates="versions", foreign_keys=[document_id])
    upload_user = relationship("User")

    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_doc_version"),
    )


class DocumentTag(Base):
    __tablename__ = "document_tag"

    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


class DocumentEditLock(Base, TimestampMixin):
    __tablename__ = "document_edit_lock"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), unique=True, nullable=False)
    locked_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document = relationship("Document", back_populates="edit_lock")
    locker = relationship("User")


class DocumentReview(Base, TimestampMixin):
    """Multi-level document approval review record."""
    __tablename__ = "document_review"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False, index=True)
    review_level: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/approved/rejected
    comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document = relationship("Document", back_populates="reviews")
    reviewer = relationship("User")

    __table_args__ = (
        UniqueConstraint("document_id", "review_level", name="uq_doc_review_level"),
    )


class CrossMatterReference(Base, TimestampMixin):
    __tablename__ = "cross_matter_reference"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matter.id"), nullable=False)
    is_readonly: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    document = relationship("Document", back_populates="cross_references")
    matter = relationship("Matter", back_populates="cross_references")
    adder = relationship("User")

    __table_args__ = (
        UniqueConstraint("document_id", "matter_id", name="uq_doc_matter_ref"),
    )
