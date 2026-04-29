from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from datetime import datetime

from app.models.base import Base, TimestampMixin


class Matter(Base, TimestampMixin):
    __tablename__ = "matter"

    id: Mapped[int] = mapped_column(primary_key=True)
    matter_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    type_id: Mapped[int] = mapped_column(ForeignKey("matter_type.id"), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    # pending, in_progress, paused, completed, cancelled
    is_key_project: Mapped[bool] = mapped_column(Boolean, default=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    current_node_id: Mapped[int | None] = mapped_column(Integer)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)

    matter_type_obj = relationship("MatterType", back_populates="matters")
    owner = relationship("User", foreign_keys=[owner_id])
    current_node = relationship(
        "WorkflowNode",
        primaryjoin="and_(foreign(Matter.current_node_id) == WorkflowNode.id)",
        post_update=True,
    )
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="matter")
    members: Mapped[list["MatterMember"]] = relationship("MatterMember", back_populates="matter")
    comments: Mapped[list["MatterComment"]] = relationship("MatterComment", back_populates="matter", order_by="MatterComment.created_at")
    nodes: Mapped[list["WorkflowNode"]] = relationship("WorkflowNode", back_populates="matter", foreign_keys="WorkflowNode.matter_id", order_by="WorkflowNode.node_order")
    cross_references: Mapped[list["CrossMatterReference"]] = relationship("CrossMatterReference", back_populates="matter")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="matter")

    __table_args__ = (
        Index("idx_matter_due", "due_date", "status"),
    )


class MatterMember(Base, TimestampMixin):
    __tablename__ = "matter_member"

    id: Mapped[int] = mapped_column(primary_key=True)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matter.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    role_in_matter: Mapped[str] = mapped_column(String(30), default="collaborator")
    # owner / collaborator

    matter = relationship("Matter", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("matter_id", "user_id", name="uq_matter_member"),
    )


class MatterComment(Base, TimestampMixin):
    __tablename__ = "matter_comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matter.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    matter = relationship("Matter", back_populates="comments")
    user = relationship("User")
