"""Task API routes — CRUD, batch operations, Excel export.

Backed by task_instance table (ProjectTask from task_manager).
"""

from io import BytesIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.permissions import RoleCode
from app.models.user import User
from app.models.task import Task  # ProjectTask alias
from app.models.task_manager import TaskTemplate

router = APIRouter()

STATUS_LABELS = {"pending": "待开始", "active": "进行中", "completed": "已完成", "cancelled": "已取消"}


# ── Schemas ──────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    template_id: int = Field(..., description="Task template ID")
    title: str = Field(..., min_length=1, max_length=200)


class TaskUpdate(BaseModel):
    title: str | None = None
    status: str | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    template_id: int
    template_name: str | None = None
    creator_id: int
    creator_name: str | None = None
    status: str
    current_stage_order: int = 1
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class BatchIdsRequest(BaseModel):
    ids: list[int]


# ── Helpers ──────────────────────────────────────────────────────

async def _get_user_name(db: AsyncSession, user_id: int) -> str:
    """Look up a user's real_name by ID."""
    result = await db.execute(select(User.real_name).where(User.id == user_id))
    row = result.scalar_one_or_none()
    return row if row else ""


async def _task_to_out(task: Task, db: AsyncSession) -> TaskOut:
    tmpl_name = None
    if task.template_id:
        tmpl_result = await db.execute(
            select(TaskTemplate.name).where(TaskTemplate.id == task.template_id)
        )
        row = tmpl_result.scalar_one_or_none()
        tmpl_name = row if row else None

    creator_name = await _get_user_name(db, task.creator_id)

    return TaskOut(
        id=task.id,
        title=task.title,
        template_id=task.template_id,
        template_name=tmpl_name,
        creator_id=task.creator_id,
        creator_name=creator_name,
        status=task.status,
        current_stage_order=task.current_stage_order,
        created_at=task.created_at.isoformat() if task.created_at else None,
        updated_at=task.updated_at.isoformat() if task.updated_at else None,
    )


def _get_user_roles(user: User) -> list[str]:
    return [r.role_code for r in (user.roles or []) if hasattr(r, "role_code")]


def _can_manage(user: User, task: Task) -> bool:
    roles = _get_user_roles(user)
    if RoleCode.ADMIN in roles:
        return True
    if task.creator_id == user.id:
        return True
    return False


# ── Routes ───────────────────────────────────────────────────────

@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    status: str = Query(None),
    keyword: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List task instances."""
    roles = _get_user_roles(current_user)
    is_admin = RoleCode.ADMIN in roles

    conditions = []
    if not is_admin:
        conditions.append(Task.creator_id == current_user.id)
    if status:
        conditions.append(Task.status == status)
    if keyword:
        conditions.append(Task.title.ilike(f"%{keyword}%"))

    where_clause = and_(*conditions) if conditions else True

    count_result = await db.execute(select(func.count(Task.id)).where(where_clause))
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Task)
        .where(where_clause)
        .order_by(Task.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    tasks = result.scalars().all()

    items = []
    for t in tasks:
        items.append(await _task_to_out(t, db))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return TaskListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=TaskOut)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task instance from a template."""
    tmpl_result = await db.execute(
        select(TaskTemplate).where(TaskTemplate.id == data.template_id)
    )
    if not tmpl_result.scalars().first():
        raise NotFoundException("Task template not found")

    task = Task(
        template_id=data.template_id,
        title=data.title,
        creator_id=current_user.id,
        status="pending",
        current_stage_order=1,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return await _task_to_out(task, db)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single task instance."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise NotFoundException("Task not found")

    roles = _get_user_roles(current_user)
    if RoleCode.ADMIN not in roles and task.creator_id != current_user.id:
        raise ForbiddenException("Access denied")

    return await _task_to_out(task, db)


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a task instance."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise NotFoundException("Task not found")

    if not _can_manage(current_user, task):
        raise ForbiddenException("Permission denied")

    if data.title is not None:
        task.title = data.title
    if data.status is not None:
        task.status = data.status

    await db.commit()
    await db.refresh(task)
    return await _task_to_out(task, db)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task instance."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise NotFoundException("Task not found")

    if not _can_manage(current_user, task):
        raise ForbiddenException("Permission denied")

    await db.delete(task)
    await db.commit()
    return {"detail": "Task deleted"}


@router.post("/batch/complete")
async def batch_complete_tasks(
    data: BatchIdsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch complete task instances."""
    result = await db.execute(select(Task).where(Task.id.in_(data.ids)))
    tasks = result.scalars().all()

    count = 0
    for task in tasks:
        if _can_manage(current_user, task):
            task.status = "completed"
            count += 1

    await db.commit()
    return {"detail": f"已完成 {count} 个任务", "count": count}


# ── Export ───────────────────────────────────────────────────────

@router.get("/export/excel")
async def export_tasks_excel(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export task instances to Excel."""
    roles = _get_user_roles(current_user)
    is_admin = RoleCode.ADMIN in roles

    conditions = []
    if not is_admin:
        conditions.append(Task.creator_id == current_user.id)
    where_clause = and_(*conditions) if conditions else True

    result = await db.execute(
        select(Task).where(where_clause).order_by(Task.created_at.desc())
    )
    tasks = result.scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "任务列表"
    ws.append(["ID", "任务名称", "模板ID", "创建人ID", "状态", "阶段", "创建时间"])

    for t in tasks:
        ws.append([
            t.id,
            t.title,
            t.template_id,
            t.creator_id,
            STATUS_LABELS.get(t.status, t.status),
            t.current_stage_order,
            t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tasks.xlsx"}
    )
