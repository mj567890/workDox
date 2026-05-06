from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta
from io import BytesIO
from openpyxl import Workbook

from app.dependencies import get_current_user, get_db, check_permission
from app.core.cache import cache
from app.core.exceptions import NotFoundException, ConflictException, ForbiddenException, ValidationException
from app.core.permissions import Permission, RoleCode
from app.core.pagination import PaginationParams
from app.models.user import User
from app.models.matter import Matter, MatterMember, MatterComment
from app.models.document import Document, DocumentVersion, MatterType
from app.models.workflow import WorkflowTemplate, WorkflowTemplateNode, WorkflowNode
from app.services.matter_service import MatterService, MatterCommentService

router = APIRouter()
matter_service = MatterService()
matter_comment_service = MatterCommentService()


# ---------- Pydantic Schemas ----------

class MatterCreate(BaseModel):
    title: str
    matter_type_id: int
    due_date: str | None = None
    description: str | None = None
    is_key_project: bool = False
    member_ids: list[int] = []


class MatterUpdate(BaseModel):
    title: str | None = None
    due_date: str | None = None
    description: str | None = None
    is_key_project: bool | None = None


class MatterStatusUpdate(BaseModel):
    status: str
    comment: str | None = None


class MemberOut(BaseModel):
    id: int
    user_id: int
    user_name: str | None
    role_in_matter: str
    avatar_url: str | None = None
    joined_at: str | None

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str


class CommentOut(BaseModel):
    id: int
    user_id: int
    user_name: str | None
    content: str
    created_at: str | None

    class Config:
        from_attributes = True


class NodeBriefOut(BaseModel):
    id: int
    node_name: str
    node_order: int
    status: str
    sla_status: str | None = None
    planned_finish_time: str | None = None
    owner_name: str | None

    class Config:
        from_attributes = True


class DocumentBriefOut(BaseModel):
    id: int
    original_name: str
    file_type: str
    version_no: int | None
    status: str
    created_at: str | None

    class Config:
        from_attributes = True


class MatterOut(BaseModel):
    id: int
    matter_no: str
    title: str
    type_id: int
    type_name: str | None
    owner_id: int
    owner_name: str | None
    status: str
    is_key_project: bool
    progress: float
    current_node_id: int | None
    current_node_name: str | None
    due_date: str | None
    description: str | None
    members: list[MemberOut] = []
    nodes: list[NodeBriefOut] = []
    recent_comments: list[CommentOut] = []
    documents: list[DocumentBriefOut] = []
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


class MatterBriefOut(BaseModel):
    id: int
    matter_no: str
    title: str
    type_name: str | None
    owner_name: str | None
    status: str
    is_key_project: bool
    progress: float
    due_date: str | None
    created_at: str | None

    class Config:
        from_attributes = True


class MatterListResponse(BaseModel):
    items: list[MatterBriefOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class AddMembersRequest(BaseModel):
    user_ids: list[int]
    role_in_matter: str = "collaborator"


class BatchAssignRequest(BaseModel):
    ids: list[int]
    assignee_id: int


# ---------- Helper Functions ----------

async def _generate_matter_no(db: AsyncSession, matter_type_id: int) -> str:
    type_result = await db.execute(select(MatterType).where(MatterType.id == matter_type_id))
    mt = type_result.scalar_one_or_none()
    type_code = mt.code if mt else "GEN"

    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")

    count_result = await db.execute(select(func.count(Matter.id)).where(
        Matter.matter_no.like(f"{type_code}-{date_part}-%")
    ))
    count = (count_result.scalar() or 0) + 1

    return f"{type_code}-{date_part}-{count:04d}"


def _user_to_dict(user: User) -> dict:
    """Convert User ORM object to a dict for service current_user param."""
    role_codes = [r.role_code for r in (user.roles or []) if hasattr(r, 'role_code')]
    return {"id": user.id, "roles": role_codes}


def _make_matter_out(m: Matter) -> MatterOut:
    members = [
        MemberOut(
            id=mb.id, user_id=mb.user_id,
            user_name=mb.user.real_name if mb.user else None,
            role_in_matter=mb.role_in_matter,
            avatar_url=mb.user.avatar_url if mb.user else None,
            joined_at=mb.created_at.isoformat() if mb.created_at else None,
        )
        for mb in (m.members or [])
    ]

    nodes = [
        NodeBriefOut(
            id=n.id, node_name=n.node_name, node_order=n.node_order,
            status=n.status, sla_status=n.sla_status,
            planned_finish_time=n.planned_finish_time.isoformat() if n.planned_finish_time else None,
            owner_name=n.owner.real_name if n.owner else None,
        )
        for n in (m.nodes or []) if hasattr(n, 'node_name')
    ]

    comments = [
        CommentOut(
            id=c.id, user_id=c.user_id,
            user_name=c.user.real_name if c.user else None,
            content=c.content,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        for c in (m.comments or []) if hasattr(c, 'content')
    ]

    return MatterOut(
        id=m.id, matter_no=m.matter_no, title=m.title,
        type_id=m.type_id,
        type_name=m.matter_type_obj.name if m.matter_type_obj else None,
        owner_id=m.owner_id,
        owner_name=m.owner.real_name if m.owner else None,
        status=m.status, is_key_project=m.is_key_project,
        progress=m.progress,
        current_node_id=m.current_node_id,
        current_node_name=m.current_node.node_name if m.current_node else None,
        due_date=m.due_date.isoformat() if m.due_date else None,
        description=m.description,
        members=members, nodes=nodes, recent_comments=comments,
        documents=[],
        created_at=m.created_at.isoformat() if m.created_at else None,
        updated_at=m.updated_at.isoformat() if m.updated_at else None,
    )


def _make_brief_out(m: Matter) -> MatterBriefOut:
    return MatterBriefOut(
        id=m.id, matter_no=m.matter_no, title=m.title,
        type_name=m.matter_type_obj.name if m.matter_type_obj else None,
        owner_name=m.owner.real_name if m.owner else None,
        status=m.status, is_key_project=m.is_key_project,
        progress=m.progress,
        due_date=m.due_date.isoformat() if m.due_date else None,
        created_at=m.created_at.isoformat() if m.created_at else None,
    )


# ---------- Matter Routes ----------

@router.get("/", response_model=MatterListResponse)
async def list_matters(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    keyword: str = Query(None),
    status: str = Query(None),
    matter_type_id: int = Query(None),
    is_key_project: bool = Query(None),
    owner_id: int = Query(None),
    sort_by: str = Query("created_at"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    filters = {}
    if keyword:
        filters["keyword"] = keyword
    if status:
        filters["status"] = status
    if matter_type_id:
        filters["type_id"] = matter_type_id
    if is_key_project is not None:
        filters["is_key_project"] = is_key_project
    if owner_id:
        filters["owner_id"] = owner_id

    current_user_dict = _user_to_dict(current_user)
    matters, total = await matter_service.get_matters(db, pagination, filters, current_user_dict)

    # Sort in-memory if custom sort; default is created_at desc handled by service
    if sort_by == "due_date":
        matters.sort(key=lambda m: m.due_date or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    elif sort_by == "title":
        matters.sort(key=lambda m: m.title, reverse=True)

    matter_list = [_make_brief_out(m) for m in matters]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return MatterListResponse(
        items=matter_list, total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/", response_model=MatterOut)
async def create_matter(
    data: MatterCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.MATTER_CREATE)),
):
    # Verify matter type exists
    type_result = await db.execute(select(MatterType).where(MatterType.id == data.matter_type_id))
    if not type_result.scalar_one_or_none():
        raise NotFoundException(resource="Matter type")

    matter_no = await _generate_matter_no(db, data.matter_type_id)

    due_date = None
    if data.due_date:
        try:
            due_date = datetime.fromisoformat(data.due_date.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationException(detail="Invalid due_date format")

    matter = Matter(
        matter_no=matter_no,
        title=data.title,
        type_id=data.matter_type_id,
        owner_id=current_user.id,
        status="pending",
        is_key_project=data.is_key_project,
        progress=0.0,
        due_date=due_date,
        description=data.description,
    )
    db.add(matter)
    await db.flush()

    # Add owner as matter member
    owner_member = MatterMember(
        matter_id=matter.id, user_id=current_user.id, role_in_matter="owner",
    )
    db.add(owner_member)

    # Add additional members
    for uid in data.member_ids:
        if uid != current_user.id:
            member = MatterMember(
                matter_id=matter.id, user_id=uid, role_in_matter="collaborator",
            )
            db.add(member)

    # Create workflow nodes from template if exists
    template_result = await db.execute(
        select(WorkflowTemplate).where(
            WorkflowTemplate.matter_type_id == data.matter_type_id,
            WorkflowTemplate.is_active == True,
        )
    )
    template = template_result.scalar_one_or_none()

    if template:
        node_templates_result = await db.execute(
            select(WorkflowTemplateNode).where(
                WorkflowTemplateNode.template_id == template.id
            ).order_by(WorkflowTemplateNode.node_order)
        )
        node_templates = node_templates_result.scalars().all()

        for nt in node_templates:
            planned = None
            if nt.sla_hours:
                planned = datetime.now(timezone.utc) + timedelta(hours=nt.sla_hours)
            node = WorkflowNode(
                matter_id=matter.id,
                node_name=nt.node_name,
                node_order=nt.node_order,
                owner_id=current_user.id,
                status="pending",
                planned_finish_time=planned,
                description=nt.description,
                required_documents_rule=nt.required_documents_rule,
            )
            db.add(node)
            if nt.node_order == 1:
                await db.flush()
                matter.current_node_id = node.id

    await db.commit()

    # Re-query with eager loads for response
    current_user_dict = _user_to_dict(current_user)
    matter = await matter_service.get_matter(db, matter.id, current_user_dict)
    return _make_matter_out(matter)


@router.get("/{matter_id}", response_model=MatterOut)
async def get_matter(
    matter_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"matter:{matter_id}"
    cached = await cache.get(cache_key)
    if cached:
        return MatterOut(**cached)

    current_user_dict = _user_to_dict(current_user)
    matter = await matter_service.get_matter(db, matter_id, current_user_dict)

    # Gather documents (service's eager load doesn't include documents)
    docs = await matter_service.get_matter_documents(db, matter_id)
    doc_list = []
    for d in docs:
        version_no = None
        if d.current_version:
            version_no = d.current_version.version_no
        doc_list.append(DocumentBriefOut(
            id=d.id, original_name=d.original_name, file_type=d.file_type,
            version_no=version_no, status=d.status,
            created_at=d.created_at.isoformat() if d.created_at else None,
        ))

    matter_out = _make_matter_out(matter)
    matter_out.documents = doc_list

    await cache.set(cache_key, matter_out.model_dump(), ttl=60)
    return matter_out


@router.put("/{matter_id}", response_model=MatterOut)
async def update_matter(
    matter_id: int,
    data: MatterUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_dict = _user_to_dict(current_user)
    matter = await matter_service.update_matter(db, matter_id, data, current_user_dict)
    await cache.delete(f"matter:{matter_id}")

    # Re-query with full eager loads
    matter = await matter_service.get_matter(db, matter.id, current_user_dict)
    return _make_matter_out(matter)


@router.delete("/{matter_id}")
async def delete_matter(
    matter_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.MATTER_DELETE)),
):
    current_user_dict = _user_to_dict(current_user)
    await matter_service.delete_matter(db, matter_id, current_user_dict)
    await cache.delete(f"matter:{matter_id}")
    return {"detail": "Matter cancelled/deleted successfully"}


@router.put("/{matter_id}/status")
async def update_matter_status(
    matter_id: int,
    data: MatterStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_dict = _user_to_dict(current_user)
    old_matter = await matter_service.get_matter(db, matter_id, current_user_dict)
    old_status = old_matter.status

    matter = await matter_service.update_status(db, matter_id, data, current_user_dict)
    await cache.delete(f"matter:{matter_id}")

    # Add a comment if provided
    if data.comment:
        from app.models.matter import MatterComment
        comment = MatterComment(
            matter_id=matter_id,
            user_id=current_user.id,
            content=f"Status changed from {old_status} to {matter.status}: {data.comment}",
        )
        db.add(comment)
        await db.commit()

    return {"detail": "Status updated", "status": matter.status}


@router.get("/{matter_id}/members", response_model=list[MemberOut])
async def list_members(
    matter_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_dict = _user_to_dict(current_user)
    # Verify access
    await matter_service.get_matter(db, matter_id, current_user_dict)

    members = await matter_service.get_members(db, matter_id)
    return [
        MemberOut(
            id=m.id, user_id=m.user_id,
            user_name=m.user.real_name if m.user else None,
            role_in_matter=m.role_in_matter,
            avatar_url=m.user.avatar_url if m.user else None,
            joined_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in members
    ]


@router.post("/{matter_id}/members")
async def add_members(
    matter_id: int,
    data: AddMembersRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.MATTER_MANAGE_MEMBERS)),
):
    current_user_dict = _user_to_dict(current_user)
    new_members = await matter_service.add_members(db, matter_id, data, current_user_dict)
    await cache.delete(f"matter:{matter_id}")
    return {"detail": "Members added", "added_user_ids": [m.user_id for m in new_members]}


@router.delete("/{matter_id}/members/{uid}")
async def remove_member(
    matter_id: int,
    uid: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.MATTER_MANAGE_MEMBERS)),
):
    current_user_dict = _user_to_dict(current_user)
    await matter_service.remove_member(db, matter_id, uid, current_user_dict)
    await cache.delete(f"matter:{matter_id}")
    return {"detail": "Member removed"}


@router.get("/{matter_id}/comments", response_model=list[CommentOut])
async def list_comments(
    matter_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_dict = _user_to_dict(current_user)
    # Verify access
    await matter_service.get_matter(db, matter_id, current_user_dict)

    pagination = PaginationParams(page=page, page_size=page_size)
    comments, _ = await matter_comment_service.get_comments(db, matter_id, pagination)

    return [
        CommentOut(
            id=c.id, user_id=c.user_id,
            user_name=c.user.real_name if c.user else None,
            content=c.content,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        for c in comments
    ]


@router.post("/{matter_id}/comments", response_model=CommentOut)
async def add_comment(
    matter_id: int,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_dict = _user_to_dict(current_user)
    # Verify access
    await matter_service.get_matter(db, matter_id, current_user_dict)

    comment = await matter_comment_service.add_comment(db, matter_id, current_user.id, data.content)
    return CommentOut(
        id=comment.id, user_id=comment.user_id,
        user_name=current_user.real_name,
        content=comment.content,
        created_at=comment.created_at.isoformat() if comment.created_at else None,
    )


@router.get("/{matter_id}/documents", response_model=list[DocumentBriefOut])
async def list_matter_documents(
    matter_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user_dict = _user_to_dict(current_user)
    # Verify access
    await matter_service.get_matter(db, matter_id, current_user_dict)

    docs = await matter_service.get_matter_documents(db, matter_id)
    doc_list = []
    for d in docs:
        version_no = None
        if d.current_version:
            version_no = d.current_version.version_no
        doc_list.append(DocumentBriefOut(
            id=d.id, original_name=d.original_name, file_type=d.file_type,
            version_no=version_no, status=d.status,
            created_at=d.created_at.isoformat() if d.created_at else None,
        ))
    return doc_list


@router.post("/batch/assign")
async def batch_assign_matters(
    data: BatchAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await matter_service.batch_assign(db, data.ids, data.assignee_id)
    return {"detail": f"\u5df2\u5206\u914d {count} \u4e2a\u4e8b\u9879", "count": count}


# ---------- Export Routes ----------

@router.get("/export/excel")
async def export_matters_excel(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pagination = PaginationParams(page=1, page_size=10000)
    filters = {}
    current_user_dict = _user_to_dict(current_user)
    matters, _ = await matter_service.get_matters(db, pagination, filters, current_user_dict)

    wb = Workbook()
    ws = wb.active
    ws.title = "\u4e8b\u9879\u5217\u8868"
    ws.append(["ID", "\u7f16\u53f7", "\u6807\u9898", "\u7c7b\u578b", "\u8d1f\u8d23\u4eba", "\u72b6\u6001", "\u8fdb\u5ea6(%)", "\u622a\u6b62\u65e5\u671f", "\u521b\u5efa\u65f6\u95f4"])

    for m in matters:
        ws.append([
            m.id,
            m.matter_no,
            m.title,
            m.matter_type_obj.name if m.matter_type_obj else '',
            m.owner.real_name if m.owner else '',
            m.status,
            m.progress,
            m.due_date.strftime('%Y-%m-%d') if m.due_date else '',
            m.created_at.strftime('%Y-%m-%d %H:%M') if m.created_at else '',
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=matters.xlsx"}
    )
