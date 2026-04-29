from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db, check_permission
from app.core.exceptions import NotFoundException, ConflictException, ForbiddenException
from app.core.permissions import Permission
from app.models.user import User
from app.models.matter import Matter, MatterMember
from app.models.workflow import WorkflowNode
from app.models.document import Document, DocumentCategory
from app.services.workflow_service import WorkflowService

router = APIRouter()
workflow_service = WorkflowService()


# ---------- Pydantic Schemas ----------

class NodeOut(BaseModel):
    id: int
    matter_id: int
    node_name: str
    node_order: int
    owner_id: int
    owner_name: str | None
    status: str
    planned_finish_time: str | None
    actual_finish_time: str | None
    description: str | None

    class Config:
        from_attributes = True


class ValidationResult(BaseModel):
    node_id: int
    is_valid: bool
    missing_documents: list[str] = []
    required_categories: list[str] = []
    existing_documents: list[str] = []


# ---------- Helper Functions ----------

def _node_to_out(node: WorkflowNode) -> NodeOut:
    """Serialize a WorkflowNode ORM object to NodeOut."""
    return NodeOut(
        id=node.id,
        matter_id=node.matter_id,
        node_name=node.node_name,
        node_order=node.node_order,
        owner_id=node.owner_id,
        owner_name=node.owner.real_name if node.owner else None,
        status=node.status,
        planned_finish_time=node.planned_finish_time.isoformat() if node.planned_finish_time else None,
        actual_finish_time=node.actual_finish_time.isoformat() if node.actual_finish_time else None,
        description=node.description,
    )


async def _get_matter_and_node(matter_id: int, node_id: int, db: AsyncSession) -> tuple[Matter | None, WorkflowNode | None]:
    """Fetch a matter and its node with owner eager-loaded, or return (None, None) on not found."""
    matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = matter_result.scalar_one_or_none()
    if not matter:
        return None, None

    node_result = await db.execute(
        select(WorkflowNode).options(
            selectinload(WorkflowNode.owner),
        ).where(
            WorkflowNode.id == node_id,
            WorkflowNode.matter_id == matter_id,
        )
    )
    node = node_result.scalar_one_or_none()
    return matter, node


async def _check_node_ownership(user: User, matter: Matter):
    """Raise ForbiddenException if user is not admin or matter owner."""
    from app.core.permissions import RoleCode

    role_codes = [r.role_code for r in (user.roles or []) if hasattr(r, 'role_code')]

    if RoleCode.ADMIN in role_codes:
        return

    if matter.owner_id == user.id:
        return

    raise ForbiddenException(detail="Only the matter owner or admin can manage nodes")


async def _check_matter_access(user: User, matter: Matter, db: AsyncSession):
    """Check if user has access to the matter (owner, member, admin, or dept leader)."""
    from app.core.permissions import RoleCode
    role_codes = [r.role_code for r in (user.roles or []) if hasattr(r, 'role_code')]
    is_admin_or_leader = RoleCode.ADMIN in role_codes or RoleCode.DEPT_LEADER in role_codes

    if is_admin_or_leader or matter.owner_id == user.id:
        return

    member_result = await db.execute(
        select(MatterMember).where(
            MatterMember.matter_id == matter.id,
            MatterMember.user_id == user.id,
        )
    )
    if not member_result.scalar_one_or_none():
        raise ForbiddenException(detail="Access denied to this matter")


# ---------- Routes ----------

@router.get("/matters/{matter_id}/nodes", response_model=list[NodeOut])
async def list_nodes(
    matter_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    matter_result = await db.execute(select(Matter).where(Matter.id == matter_id))
    matter = matter_result.scalar_one_or_none()
    if not matter:
        raise NotFoundException(resource="Matter")

    await _check_matter_access(current_user, matter, db)

    nodes = await workflow_service.get_nodes(db, matter_id)
    return [_node_to_out(n) for n in nodes]


@router.put("/matters/{matter_id}/nodes/{node_id}/advance", response_model=NodeOut)
async def advance_node(
    matter_id: int,
    node_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.MATTER_ADVANCE_NODE)),
):
    matter, node = await _get_matter_and_node(matter_id, node_id, db)
    if not matter:
        raise NotFoundException(resource="Matter")
    if not node:
        raise NotFoundException(resource="Workflow node")

    await _check_node_ownership(current_user, matter)

    # Status validation (route layer - business rule)
    if node.status in ("completed", "skipped"):
        raise ConflictException(detail=f"Node is already {node.status}")
    if node.status not in ("pending", "in_progress", "rolled_back"):
        raise ConflictException(detail=f"Cannot advance node with status: {node.status}")

    node = await workflow_service.advance_node(db, matter_id, node_id, current_user.id)
    return _node_to_out(node)


@router.put("/matters/{matter_id}/nodes/{node_id}/rollback", response_model=NodeOut)
async def rollback_node(
    matter_id: int,
    node_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.MATTER_ADVANCE_NODE)),
):
    matter, node = await _get_matter_and_node(matter_id, node_id, db)
    if not matter:
        raise NotFoundException(resource="Matter")
    if not node:
        raise NotFoundException(resource="Workflow node")

    await _check_node_ownership(current_user, matter)

    # Status validation (route layer)
    if node.status != "completed":
        raise ConflictException(detail=f"Cannot rollback node with status: {node.status}")

    node = await workflow_service.rollback_node(db, matter_id, node_id, current_user.id)
    return _node_to_out(node)


@router.put("/matters/{matter_id}/nodes/{node_id}/skip", response_model=NodeOut)
async def skip_node(
    matter_id: int,
    node_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.MATTER_ADVANCE_NODE)),
):
    matter, node = await _get_matter_and_node(matter_id, node_id, db)
    if not matter:
        raise NotFoundException(resource="Matter")
    if not node:
        raise NotFoundException(resource="Workflow node")

    await _check_node_ownership(current_user, matter)

    # Status validation (route layer)
    if node.status in ("completed", "skipped"):
        raise ConflictException(detail=f"Node is already {node.status}")

    node = await workflow_service.skip_node(db, matter_id, node_id, current_user.id)
    return _node_to_out(node)


@router.get("/matters/{matter_id}/nodes/{node_id}/validate", response_model=ValidationResult)
async def validate_node(
    matter_id: int,
    node_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    matter, node = await _get_matter_and_node(matter_id, node_id, db)
    if not matter:
        raise NotFoundException(resource="Matter")
    if not node:
        raise NotFoundException(resource="Workflow node")

    missing_docs = []
    existing_docs = []
    required_categories = []

    # Check required documents rule
    if node.required_documents_rule:
        rule = node.required_documents_rule
        category_codes = rule.get("category_codes", [])
        min_count = rule.get("min_count", 0)

        if category_codes:
            required_categories = category_codes

            # Get category IDs from codes
            cat_result = await db.execute(
                select(DocumentCategory.id, DocumentCategory.code).where(
                    DocumentCategory.code.in_(category_codes)
                )
            )
            cat_map = {row[1]: row[0] for row in cat_result.all()}
            cat_ids = list(cat_map.values())

            if cat_ids:
                docs_result = await db.execute(
                    select(Document.original_name, DocumentCategory.code).join(
                        DocumentCategory, Document.category_id == DocumentCategory.id
                    ).where(
                        Document.matter_id == matter_id,
                        Document.is_deleted == False,
                        Document.category_id.in_(cat_ids),
                    )
                )
                existing = docs_result.all()

                existing_cats = set()
                for doc_name, code in existing:
                    existing_docs.append(doc_name)
                    existing_cats.add(code)

                for code in category_codes:
                    if code not in existing_cats:
                        missing_docs.append(f"Document with category '{code}' is required")

                if min_count > 0 and len(existing) < min_count:
                    missing_docs.append(f"Minimum {min_count} documents required, only {len(existing)} found")

    is_valid = len(missing_docs) == 0

    return ValidationResult(
        node_id=node_id,
        is_valid=is_valid,
        missing_documents=missing_docs,
        required_categories=required_categories,
        existing_documents=existing_docs,
    )
