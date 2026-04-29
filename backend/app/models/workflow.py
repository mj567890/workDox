from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from app.models.base import Base, TimestampMixin


class WorkflowTemplate(Base, TimestampMixin):
    __tablename__ = "workflow_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    matter_type_id: Mapped[int] = mapped_column(ForeignKey("matter_type.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text)

    matter_type_obj = relationship("MatterType", back_populates="workflow_templates")
    template_nodes: Mapped[list["WorkflowTemplateNode"]] = relationship(
        "WorkflowTemplateNode", back_populates="template", order_by="WorkflowTemplateNode.node_order"
    )


class WorkflowTemplateNode(Base, TimestampMixin):
    __tablename__ = "workflow_template_node"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("workflow_template.id"), nullable=False)
    node_name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_order: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_role: Mapped[str] = mapped_column(String(50), nullable=False)  # matter_owner, dept_leader, etc.
    sla_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)  # SLA 时限（小时），None 表示无时限
    required_documents_rule: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)

    template = relationship("WorkflowTemplate", back_populates="template_nodes")

    __table_args__ = (
        UniqueConstraint("template_id", "node_order", name="uq_template_node_order"),
    )


class WorkflowNode(Base, TimestampMixin):
    __tablename__ = "workflow_node"

    id: Mapped[int] = mapped_column(primary_key=True)
    matter_id: Mapped[int] = mapped_column(ForeignKey("matter.id"), nullable=False)
    node_name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_order: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending, in_progress, completed, skipped, rolled_back
    planned_finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_status: Mapped[str | None] = mapped_column(String(20), default=None)  # on_track, at_risk, overdue
    description: Mapped[str | None] = mapped_column(Text)
    required_documents_rule: Mapped[dict | None] = mapped_column(JSON)

    matter = relationship("Matter", back_populates="nodes", foreign_keys=[matter_id])
    owner = relationship("User")

    __table_args__ = (
        UniqueConstraint("matter_id", "node_order", name="uq_matter_node_order"),
    )
