from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.models.base import Base, TimestampMixin


class Task(Base, TimestampMixin):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matter.id"), nullable=False)
    node_id: Mapped[int | None] = mapped_column(ForeignKey("workflow_node.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    assigner_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    assignee_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending, in_progress, completed, cancelled
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    # low, normal, high, urgent
    due_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)

    matter = relationship("Matter", back_populates="tasks")
    node = relationship("WorkflowNode")
    assigner = relationship("User", foreign_keys=[assigner_id])
    assignee = relationship("User", foreign_keys=[assignee_id])


class Notification(Base, TimestampMixin):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # task_assigned, node_advanced, document_uploaded, version_update, lock_notice, due_warning, overdue_alert
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    related_matter_id: Mapped[int | None] = mapped_column(ForeignKey("matter.id"))

    user = relationship("User", foreign_keys=[user_id])
    related_matter = relationship("Matter")

    __table_args__ = (
        Index("idx_notification_user_read", "user_id", "is_read"),
    )


class OperationLog(Base, TimestampMixin):
    __tablename__ = "operation_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # login, upload, download, delete, lock, unlock, create_matter, update_matter, advance_node, etc.
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # document, matter, workflow_node, user, etc.
    target_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))

    user = relationship("User")

    __table_args__ = (
        Index("idx_oplog_user_time", "user_id", "created_at"),
    )
