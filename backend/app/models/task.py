from sqlalchemy import String, Integer, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# ── Definition layer (user-designed) ──────────────────────────

class TaskTemplate(Base, TimestampMixin):
    __tablename__ = "task_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    stages: Mapped[list["StageTemplate"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="StageTemplate.order"
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="template")


class StageTemplate(Base, TimestampMixin):
    __tablename__ = "stage_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("task_template.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    deadline_offset_days: Mapped[int | None] = mapped_column(Integer)

    template = relationship("TaskTemplate", back_populates="stages")
    slots: Mapped[list["SlotTemplate"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan", order_by="SlotTemplate.sort_order"
    )


class SlotTemplate(Base, TimestampMixin):
    __tablename__ = "slot_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_template_id: Mapped[int] = mapped_column(ForeignKey("stage_template.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    file_type_hints: Mapped[list[str] | None] = mapped_column(JSON)
    auto_tags: Mapped[list[str] | None] = mapped_column(JSON)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    stage = relationship("StageTemplate", back_populates="slots")


# ── Instance layer (runtime) ──────────────────────────────────

class Task(Base, TimestampMixin):
    __tablename__ = "task_instance"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("task_template.id"), nullable=False)
    matter_id: Mapped[int | None] = mapped_column(ForeignKey("matter.id"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | active | completed | cancelled
    current_stage_order: Mapped[int] = mapped_column(Integer, default=1)
    creator_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    template = relationship("TaskTemplate", back_populates="tasks")
    stages: Mapped[list["Stage"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="Stage.order"
    )


class Stage(Base, TimestampMixin):
    __tablename__ = "task_stage"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("task_instance.id", ondelete="CASCADE"), nullable=False)
    stage_template_id: Mapped[int | None] = mapped_column(ForeignKey("stage_template.id"))
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="locked")  # locked | in_progress | completed
    notes: Mapped[str | None] = mapped_column(Text)

    task = relationship("Task", back_populates="stages")
    slots: Mapped[list["Slot"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan", order_by="Slot.id"
    )


class Slot(Base, TimestampMixin):
    __tablename__ = "task_slot"

    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[int] = mapped_column(ForeignKey("task_stage.id", ondelete="CASCADE"), nullable=False)
    slot_template_id: Mapped[int | None] = mapped_column(ForeignKey("slot_template.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | filled | waived
    waive_reason: Mapped[str | None] = mapped_column(Text)
    maturity: Mapped[str | None] = mapped_column(String(20))  # draft | revision | final | custom
    maturity_note: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"))

    stage = relationship("Stage", back_populates="slots")
    document = relationship("Document", foreign_keys=[document_id])
    versions: Mapped[list["SlotVersion"]] = relationship(
        back_populates="slot", cascade="all, delete-orphan", order_by="SlotVersion.created_at"
    )


class SlotVersion(Base, TimestampMixin):
    __tablename__ = "slot_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("task_slot.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"), nullable=False)
    maturity: Mapped[str | None] = mapped_column(String(20))
    maturity_note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    slot = relationship("Slot", back_populates="versions")
    document = relationship("Document", foreign_keys=[document_id])
    creator = relationship("User", foreign_keys=[created_by])
