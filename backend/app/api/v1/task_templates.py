from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.task_management_service import TaskTemplateService

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────

class SlotTemplateIn(BaseModel):
    name: str
    description: str | None = None
    is_required: bool = True
    file_type_hints: list[str] | None = None
    auto_tags: list[str] | None = None
    sort_order: int = 0


class StageTemplateIn(BaseModel):
    name: str
    order: int | None = None
    description: str | None = None
    deadline_offset_days: int | None = None
    slots: list[SlotTemplateIn] = []


class TemplateCreate(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None
    stages: list[StageTemplateIn] = []


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None


class StageCreate(BaseModel):
    name: str
    order: int | None = None
    description: str | None = None
    deadline_offset_days: int | None = None


class StageUpdate(BaseModel):
    name: str | None = None
    order: int | None = None
    description: str | None = None
    deadline_offset_days: int | None = None


class SlotCreate(BaseModel):
    name: str
    description: str | None = None
    is_required: bool = True
    file_type_hints: list[str] | None = None
    auto_tags: list[str] | None = None
    sort_order: int = 0


class SlotUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_required: bool | None = None
    file_type_hints: list[str] | None = None
    auto_tags: list[str] | None = None
    sort_order: int | None = None


class ReorderIn(BaseModel):
    ids: list[int]


# ── Template CRUD ────────────────────────────────────────────

@router.get("")
async def list_templates(
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    templates = await TaskTemplateService().list_templates(db, category)
    return {"items": templates, "total": len(templates)}


@router.post("")
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskTemplateService().create_template(db, data.model_dump())


@router.get("/{template_id}")
async def get_template(template_id: int, db: AsyncSession = Depends(get_db)):
    return await TaskTemplateService().get_template(db, template_id)


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    await TaskTemplateService().update_template(db, template_id, data.model_dump(exclude_unset=True))
    return {"detail": "Updated"}


@router.delete("/{template_id}")
async def delete_template(template_id: int, db: AsyncSession = Depends(get_db)):
    await TaskTemplateService().delete_template(db, template_id)
    return {"detail": "Deleted"}


@router.post("/{template_id}/clone")
async def clone_template(template_id: int, db: AsyncSession = Depends(get_db)):
    return await TaskTemplateService().clone_template(db, template_id)


# ── Stage management ─────────────────────────────────────────

@router.post("/{template_id}/stages")
async def add_stage(
    template_id: int,
    data: StageCreate,
    db: AsyncSession = Depends(get_db),
):
    return await TaskTemplateService().add_stage(db, template_id, data.model_dump())


@router.put("/{template_id}/stages/{stage_id}")
async def update_stage(
    template_id: int,
    stage_id: int,
    data: StageUpdate,
    db: AsyncSession = Depends(get_db),
):
    await TaskTemplateService().update_stage(db, template_id, stage_id, data.model_dump(exclude_unset=True))
    return {"detail": "Updated"}


@router.delete("/{template_id}/stages/{stage_id}")
async def delete_stage(template_id: int, stage_id: int, db: AsyncSession = Depends(get_db)):
    await TaskTemplateService().delete_stage(db, template_id, stage_id)
    return {"detail": "Deleted"}


@router.put("/{template_id}/stages/reorder")
async def reorder_stages(template_id: int, data: ReorderIn, db: AsyncSession = Depends(get_db)):
    await TaskTemplateService().reorder_stages(db, template_id, data.ids)
    return {"detail": "Reordered"}


# ── Slot management ──────────────────────────────────────────

@router.post("/{template_id}/stages/{stage_id}/slots")
async def add_slot(
    template_id: int,
    stage_id: int,
    data: SlotCreate,
    db: AsyncSession = Depends(get_db),
):
    return await TaskTemplateService().add_slot(db, template_id, stage_id, data.model_dump())


@router.put("/{template_id}/stages/{stage_id}/slots/{slot_id}")
async def update_slot(
    template_id: int,
    stage_id: int,
    slot_id: int,
    data: SlotUpdate,
    db: AsyncSession = Depends(get_db),
):
    await TaskTemplateService().update_slot(db, template_id, stage_id, slot_id, data.model_dump(exclude_unset=True))
    return {"detail": "Updated"}


@router.delete("/{template_id}/stages/{stage_id}/slots/{slot_id}")
async def delete_slot(
    template_id: int, stage_id: int, slot_id: int,
    db: AsyncSession = Depends(get_db),
):
    await TaskTemplateService().delete_slot(db, template_id, stage_id, slot_id)
    return {"detail": "Deleted"}


@router.put("/{template_id}/stages/{stage_id}/slots/reorder")
async def reorder_slots(
    template_id: int, stage_id: int,
    data: ReorderIn, db: AsyncSession = Depends(get_db),
):
    await TaskTemplateService().reorder_slots(db, template_id, stage_id, data.ids)
    return {"detail": "Reordered"}
