from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from io import BytesIO
from openpyxl import Workbook

from app.dependencies import get_current_user, get_db
from app.core.exceptions import NotFoundException, ForbiddenException, ValidationException
from app.core.pagination import PaginationParams
from app.models.user import User
from app.models.task import Task
from app.models.matter import Matter, MatterMember
from app.services.task_service import TaskService

router = APIRouter()
task_service = TaskService()


# ---------- Pydantic Schemas ----------

class TaskCreate(BaseModel):
    matter_id: int
    node_id: int | None = None
    title: str
    assignee_id: int
    status: str = "pending"
    priority: str = "normal"
    due_time: str | None = None
    description: str | None = None

    model_config = {"validate_assignment": False}


class TaskUpdate(BaseModel):
    title: str | None = None
    assignee_id: int | None = None
    status: str | None = None
    priority: str | None = None
    due_time: str | None = None
    description: str | None = None


class TaskOut(BaseModel):
    id: int
    matter_id: int
    matter_title: str | None
    node_id: int | None
    node_name: str | None
    title: str
    assigner_id: int
    assigner_name: str | None
    assignee_id: int
    assignee_name: str | None
    status: str
    priority: str
    due_time: str | None
    description: str | None
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class BatchIdsRequest(BaseModel):
    ids: list[int]


# ---------- Helper Functions ----------

def _task_to_out(task: Task) -> TaskOut:
    """Serialize a Task ORM object to TaskOut response schema."""
    return TaskOut(
        id=task.id,
        matter_id=task.matter_id,
        matter_title=task.matter.title if task.matter else None,
        node_id=task.node_id,
        node_name=task.node.node_name if task.node else None,
        title=task.title,
        assigner_id=task.assigner_id,
        assigner_name=task.assigner.real_name if task.assigner else None,
        assignee_id=task.assignee_id,
        assignee_name=task.assignee.real_name if task.assignee else None,
        status=task.status,
        priority=task.priority,
        due_time=task.due_time.isoformat() if task.due_time else None,
        description=task.description,
        created_at=task.created_at.isoformat() if task.created_at else None,
        updated_at=task.updated_at.isoformat() if task.updated_at else None,
    )


async def _can_manage_tasks_in_matter(user: User, task: Task, db: AsyncSession) -> bool:
    """Check if user can manage a task (admin, matter owner, or assigner)."""
    from app.core.permissions import RoleCode

    role_codes = [r.role_code for r in (user.roles or []) if hasattr(r, 'role_code')]
    if RoleCode.ADMIN in role_codes:
        return True
    if task.assigner_id == user.id:
        return True

    matter_result = await db.execute(select(Matter).where(Matter.id == task.matter_id))
    matter = matter_result.scalar_one_or_none()
    if matter and matter.owner_id == user.id:
        return True

    return False


async def _get_user_roles(current_user: User) -> list[str]:
    """Extract role codes from a User object."""
    return [r.role_code for r in (current_user.roles or []) if hasattr(r, 'role_code')]


async def _get_accessible_matter_ids(current_user: User, db: AsyncSession) -> list[int]:
    """Get matter IDs the user is a member of."""
    from app.core.permissions import RoleCode
    role_codes = await _get_user_roles(current_user)
    if RoleCode.ADMIN in role_codes or RoleCode.DEPT_LEADER in role_codes:
        return []
    member_result = await db.execute(
        select(MatterMember.matter_id).where(MatterMember.user_id == current_user.id)
    )
    return [row[0] for row in member_result.all()]


async def _build_user_dict(current_user: User, db: AsyncSession) -> dict:
    """Build a current_user dict for service calls from a User model."""
    roles = await _get_user_roles(current_user)
    accessible = await _get_accessible_matter_ids(current_user, db)
    user_dict = {"id": current_user.id, "roles": roles}
    if accessible:
        accessible.append(-1)  # sentinel
        user_dict["accessible_matter_ids"] = accessible
    return user_dict


# ---------- Routes ----------

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    status: str = Query(None),
    priority: str = Query(None),
    assignee_id: int = Query(None),
    matter_id: int = Query(None),
    keyword: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    filters = {}
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    if assignee_id:
        filters["assignee_id"] = assignee_id
    if matter_id:
        filters["matter_id"] = matter_id
    if keyword:
        filters["keyword"] = keyword

    user_dict = await _build_user_dict(current_user, db)

    items, total = await task_service.get_tasks(db, pagination, filters, user_dict)

    task_list = [_task_to_out(t) for t in items]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return TaskListResponse(
        items=task_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/", response_model=TaskOut)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Parse due_time from string to datetime before passing to service
    due_time = None
    if data.due_time:
        try:
            due_time = datetime.fromisoformat(data.due_time.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationException(detail="Invalid due_time format")
    data.due_time = due_time

    task = await task_service.create_task(db, data, current_user.id)

    # Send email notification to assignee (route-layer concern)
    try:
        assignee_result = await db.execute(
            select(User).where(User.id == data.assignee_id)
        )
        assignee_user = assignee_result.scalar_one_or_none()
        if assignee_user and assignee_user.email:
            from app.utils.email_sender import email_sender, PRIORITY_LABELS
            import asyncio
            asyncio.create_task(email_sender.send(
                to_email=assignee_user.email,
                template_name="task_assigned",
                context={
                    "assignee_name": assignee_user.real_name,
                    "assigner_name": current_user.real_name,
                    "task_title": data.title,
                    "matter_title": task.matter.title if task.matter else "",
                    "priority_label": PRIORITY_LABELS.get(data.priority, data.priority),
                    "due_time": task.due_time.strftime("%Y-%m-%d %H:%M") if task.due_time else None,
                }
            ))
    except Exception:
        pass  # Email failure should not block task creation

    return _task_to_out(task)


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, task_id)

    # Access control check
    from app.core.permissions import RoleCode
    role_codes = await _get_user_roles(current_user)
    is_admin = RoleCode.ADMIN in role_codes

    has_access = (
        is_admin
        or task.assignee_id == current_user.id
        or task.assigner_id == current_user.id
    )
    if not has_access:
        member_result = await db.execute(
            select(MatterMember).where(
                MatterMember.matter_id == task.matter_id,
                MatterMember.user_id == current_user.id,
            )
        )
        if not member_result.scalar_one_or_none():
            raise ForbiddenException(detail="Access denied to this task")

    return _task_to_out(task)


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, task_id)

    if not await _can_manage_tasks_in_matter(current_user, task, db):
        raise ForbiddenException(detail="You do not have permission to update this task")

    # Parse due_time from string to datetime
    if data.due_time is not None and data.due_time != "":
        try:
            parsed = datetime.fromisoformat(data.due_time.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationException(detail="Invalid due_time format")
        data.due_time = parsed
    elif data.due_time == "":
        data.due_time = None

    user_dict = {"id": current_user.id, "roles": await _get_user_roles(current_user)}
    task = await task_service.update_task(db, task_id, data, user_dict)

    return _task_to_out(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(db, task_id)

    if not await _can_manage_tasks_in_matter(current_user, task, db):
        raise ForbiddenException(detail="You do not have permission to delete this task")

    await task_service.delete_task(db, task_id)
    return {"detail": "Task deleted"}


@router.post("/batch/complete")
async def batch_complete_tasks(
    data: BatchIdsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await task_service.batch_complete_tasks(db, data.ids)
    return {"detail": f"\u5df2\u5b8c\u6210 {count} \u4e2a\u4efb\u52a1", "count": count}


# ---------- Export Routes ----------

@router.get("/export/excel")
async def export_tasks_excel(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_dict = await _build_user_dict(current_user, db)
    tasks = await task_service.get_tasks_for_export(db, user_dict)

    wb = Workbook()
    ws = wb.active
    ws.title = "\u4efb\u52a1\u5217\u8868"
    ws.append(["ID", "\u4efb\u52a1\u540d\u79f0", "\u6240\u5c5e\u4e8b\u9879", "\u5206\u914d\u4eba", "\u8d1f\u8d23\u4eba", "\u72b6\u6001", "\u4f18\u5148\u7ea7", "\u622a\u6b62\u65f6\u95f4", "\u521b\u5efa\u65f6\u95f4"])

    for t in tasks:
        ws.append([
            t.id,
            t.title,
            t.matter.title if t.matter else '',
            t.assigner.real_name if t.assigner else '',
            t.assignee.real_name if t.assignee else '',
            t.status,
            t.priority,
            t.due_time.strftime('%Y-%m-%d %H:%M') if t.due_time else '',
            t.created_at.strftime('%Y-%m-%d %H:%M') if t.created_at else '',
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tasks.xlsx"}
    )
