from sqlalchemy import String, Boolean, Integer, Float, DateTime, Text, ForeignKey, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from datetime import datetime
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TimestampMixin


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


# Association table for document-tag many-to-many
class DocumentTag(Base):
    __tablename__ = "document_tag"

    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tag.id"), primary_key=True)


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
    category_id: Mapped[int | None] = mapped_column(ForeignKey("document_category.id"))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    current_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    permission_scope: Mapped[str] = mapped_column(String(30), default="matter")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    preview_pdf_path: Mapped[str | None] = mapped_column(String(500))
    preview_html_path: Mapped[str | None] = mapped_column(String(500))
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(768), nullable=True)

    owner = relationship("User")
    category = relationship("DocumentCategory", back_populates="documents")
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary="document_tag", back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", order_by="DocumentVersion.version_no.desc()"
    )
    current_version: Mapped["DocumentVersion | None"] = relationship(
        "DocumentVersion",
        primaryjoin="and_(foreign(Document.current_version_id) == DocumentVersion.id)",
        post_update=True,
    )
    edit_lock = relationship("DocumentEditLock", back_populates="document", uselist=False)
    reviews: Mapped[list["DocumentReview"]] = relationship(
        "DocumentReview", back_populates="document", order_by="DocumentReview.review_level"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", order_by="DocumentChunk.chunk_index"
    )

    __table_args__ = (
        Index("idx_document_search",
              text("to_tsvector('simple', coalesce(original_name,'') || ' ' || coalesce(description,''))"),
              postgresql_using="gin"),
    )


class DocumentVersion(Base, TimestampMixin):
    __tablename__ = "document_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    upload_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    change_note: Mapped[str | None] = mapped_column(String(500))
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    checksum: Mapped[str | None] = mapped_column(String(64))

    document = relationship("Document", back_populates="versions")
    upload_user = relationship("User")


class DocumentEditLock(Base, TimestampMixin):
    __tablename__ = "document_edit_lock"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False)
    locked_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    document = relationship("Document", back_populates="edit_lock")
    locker = relationship("User")


class DocumentReview(Base, TimestampMixin):
    __tablename__ = "document_review"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    review_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    comment: Mapped[str | None] = mapped_column(Text)

    document = relationship("Document", back_populates="reviews")
    reviewer = relationship("User")
