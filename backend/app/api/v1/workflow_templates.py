from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, check_permission
from app.core.pagination import PaginationParams
from app.core.permissions import Permission
from app.models.user import User
from app.services.workflow_service import WorkflowService

router = APIRouter()
workflow_service = WorkflowService()


# ---------- Pydantic Schemas ----------

class NodeRule(BaseModel):
    category_codes: list[str] = []
    min_count: int = 0
    description: str | None = None


class TemplateNodeCreate(BaseModel):
    node_name: str
    node_order: int
    owner_role: str
    sla_hours: int | None = None
    required_documents_rule: NodeRule | None = None
    description: str | None = None


class TemplateNodeUpdate(BaseModel):
    node_name: str | None = None
    node_order: int | None = None
    owner_role: str | None = None
    required_documents_rule: NodeRule | None = None
    description: str | None = None


class TemplateNodeOut(BaseModel):
    id: int
    node_name: str
    node_order: int
    owner_role: str
    sla_hours: int | None = None
    required_documents_rule: dict | None
    description: str | None

    class Config:
        from_attributes = True


class TemplateCreate(BaseModel):
    name: str
    matter_type_id: int
    is_active: bool = True
    description: str | None = None
    nodes: list[TemplateNodeCreate] = []


class TemplateUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    description: str | None = None


class TemplateOut(BaseModel):
    id: int
    name: str
    matter_type_id: int
    matter_type_name: str | None
    is_active: bool
    description: str | None
    nodes: list[TemplateNodeOut] = []
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


class TemplateBriefOut(BaseModel):
    id: int
    name: str
    matter_type_id: int
    matter_type_name: str | None
    is_active: bool
    description: str | None
    node_count: int
    created_at: str | None

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    items: list[TemplateBriefOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------- Helper ----------

def _template_to_out(template) -> TemplateOut:
    """Serialize a WorkflowTemplate ORM object to TemplateOut."""
    nodes = template.template_nodes or []
    return TemplateOut(
        id=template.id,
        name=template.name,
        matter_type_id=template.matter_type_id,
        matter_type_name=template.matter_type_obj.name if template.matter_type_obj else None,
        is_active=template.is_active,
        description=template.description,
        nodes=[
            TemplateNodeOut(
                id=n.id,
                node_name=n.node_name,
                node_order=n.node_order,
                owner_role=n.owner_role,
                sla_hours=n.sla_hours,
                required_documents_rule=n.required_documents_rule,
                description=n.description,
            )
            for n in nodes
        ],
        created_at=template.created_at.isoformat() if template.created_at else None,
        updated_at=template.updated_at.isoformat() if template.updated_at else None,
    )


def _template_to_brief(template) -> TemplateBriefOut:
    """Serialize a WorkflowTemplate to a brief summary."""
    nodes = template.template_nodes or []
    return TemplateBriefOut(
        id=template.id,
        name=template.name,
        matter_type_id=template.matter_type_id,
        matter_type_name=template.matter_type_obj.name if template.matter_type_obj else None,
        is_active=template.is_active,
        description=template.description,
        node_count=len(nodes),
        created_at=template.created_at.isoformat() if template.created_at else None,
    )


# ---------- Routes ----------

@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    matter_type_id: int = Query(None),
    is_active: bool = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pagination = PaginationParams(page=page, page_size=page_size)
    templates, total = await workflow_service.get_templates(
        db, pagination,
        matter_type_id=matter_type_id,
        is_active=is_active,
    )

    items = [_template_to_brief(t) for t in templates]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return TemplateListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/templates", response_model=TemplateOut)
async def create_template(
    data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.WORKFLOW_TEMPLATE_MANAGE)),
):
    template = await workflow_service.create_template(db, data)
    return _template_to_out(template)


@router.get("/templates/{template_id}", response_model=TemplateOut)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    template = await workflow_service.get_template(db, template_id)
    return _template_to_out(template)


@router.put("/templates/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.WORKFLOW_TEMPLATE_MANAGE)),
):
    template = await workflow_service.update_template(db, template_id, data)
    return _template_to_out(template)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.WORKFLOW_TEMPLATE_MANAGE)),
):
    await workflow_service.delete_template(db, template_id)
    return {"detail": "Workflow template deleted"}
