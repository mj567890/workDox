from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.task_management_service import TaskInstanceService

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────

class TaskCreate(BaseModel):
    template_id: int
    title: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    status: str | None = None


class SlotUpload(BaseModel):
    document_id: int
    maturity: str = "draft"
    maturity_note: str | None = None


class MaturityUpdate(BaseModel):
    maturity: str
    maturity_note: str | None = None


class WaiveIn(BaseModel):
    reason: str


# ── Task CRUD ────────────────────────────────────────────────

@router.get("")
async def list_tasks(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    tasks = await TaskInstanceService().list_tasks(db, status)
    return {"items": tasks, "total": len(tasks)}


@router.post("")
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskInstanceService().create_task(db, data.model_dump(), current_user.id)


@router.get("/{task_id}")
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    return await TaskInstanceService().get_task(db, task_id)


@router.put("/{task_id}")
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await TaskInstanceService().update_task(db, task_id, data.model_dump(exclude_unset=True))


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    await TaskInstanceService().delete_task(db, task_id)
    return {"detail": "Deleted"}


@router.put("/{task_id}/advance")
async def advance_stage(task_id: int, db: AsyncSession = Depends(get_db)):
    return await TaskInstanceService().advance_stage(db, task_id)


@router.get("/{task_id}/board")
async def get_board(task_id: int, db: AsyncSession = Depends(get_db)):
    return await TaskInstanceService().get_board(db, task_id)


# ── Slot operations ──────────────────────────────────────────

@router.post("/{task_id}/stages/{stage_id}/slots/{slot_id}/upload")
async def upload_to_slot(
    task_id: int, stage_id: int, slot_id: int,
    data: SlotUpload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskInstanceService().upload_to_slot(
        db, task_id, stage_id, slot_id,
        data.document_id, data.maturity, data.maturity_note,
        user_id=current_user.id,
    )


@router.put("/{task_id}/stages/{stage_id}/slots/{slot_id}/replace")
async def replace_slot_document(
    task_id: int, stage_id: int, slot_id: int,
    data: SlotUpload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaskInstanceService().replace_slot_document(
        db, task_id, stage_id, slot_id,
        data.document_id, data.maturity, data.maturity_note,
        user_id=current_user.id,
    )


@router.delete("/{task_id}/stages/{stage_id}/slots/{slot_id}/document")
async def remove_slot_document(
    task_id: int, stage_id: int, slot_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await TaskInstanceService().remove_slot_document(db, task_id, stage_id, slot_id)


@router.put("/{task_id}/stages/{stage_id}/slots/{slot_id}/maturity")
async def update_slot_maturity(
    task_id: int, stage_id: int, slot_id: int,
    data: MaturityUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await TaskInstanceService().update_slot_maturity(
        db, task_id, stage_id, slot_id, data.maturity, data.maturity_note
    )


@router.put("/{task_id}/stages/{stage_id}/slots/{slot_id}/waive")
async def waive_slot(
    task_id: int, stage_id: int, slot_id: int,
    data: WaiveIn,
    db: AsyncSession = Depends(get_db),
):
    return await TaskInstanceService().waive_slot(db, task_id, stage_id, slot_id, data.reason)


@router.put("/{task_id}/stages/{stage_id}/slots/{slot_id}/unwaive")
async def unwaive_slot(
    task_id: int, stage_id: int, slot_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await TaskInstanceService().unwaive_slot(db, task_id, stage_id, slot_id)


@router.get("/{task_id}/stages/{stage_id}/slots/{slot_id}/versions")
async def get_slot_versions(
    task_id: int, stage_id: int, slot_id: int,
    db: AsyncSession = Depends(get_db),
):
    versions = await TaskInstanceService().get_slot_versions(db, task_id, stage_id, slot_id)
    return {"items": versions, "total": len(versions)}
