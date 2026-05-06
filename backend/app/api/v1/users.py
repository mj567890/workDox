from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_current_user, get_db, check_permission
from app.core.cache import cache
from app.core.exceptions import NotFoundException, ConflictException, ForbiddenException
from app.core.permissions import Permission, RoleCode
from app.core.security import hash_password, verify_password
from app.core.pagination import PaginationParams
from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.services.user_service import UserService, RoleService, DepartmentService, DocumentCategoryService, TagService

router = APIRouter()
user_service = UserService()
role_service = RoleService()
department_service = DepartmentService()
category_service = DocumentCategoryService()
tag_service = TagService()


# ---------- Pydantic Schemas ----------

class UserCreate(BaseModel):
    username: str
    password: str
    real_name: str
    email: str | None = None
    phone: str | None = None
    department_id: int | None = None
    role_ids: list[int] = []
    status: str = "active"


class UserUpdate(BaseModel):
    real_name: str | None = None
    email: str | None = None
    phone: str | None = None
    department_id: int | None = None
    avatar_url: str | None = None
    role_ids: list[int] | None = None


class UserOut(BaseModel):
    id: int
    username: str
    real_name: str
    email: str | None
    phone: str | None
    department_id: int | None
    department_name: str | None
    avatar_url: str | None
    status: str
    role_names: list[str]
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class RoleCreate(BaseModel):
    role_name: str
    role_code: str
    description: str | None = None


class RoleUpdate(BaseModel):
    role_name: str | None = None
    description: str | None = None


class RoleOut(BaseModel):
    id: int
    role_name: str
    role_code: str
    description: str | None

    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    name: str
    code: str
    parent_id: int | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    parent_id: int | None = None


class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


class DepartmentTreeOut(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None
    children: list["DepartmentTreeOut"] = []

    class Config:
        from_attributes = True


class DocumentCategoryCreate(BaseModel):
    name: str
    code: str
    description: str | None = None
    sort_order: int = 0


class DocumentCategoryUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    sort_order: int | None = None


class DocumentCategoryOut(BaseModel):
    id: int
    name: str
    code: str
    description: str | None
    sort_order: int
    is_system: bool
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    name: str
    color: str = "#409EFF"


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class TagOut(BaseModel):
    id: int
    name: str
    color: str
    created_at: str | None
    updated_at: str | None

    class Config:
        from_attributes = True


def _user_to_out(u: User) -> UserOut:
    """Format a User ORM object to UserOut response schema."""
    return UserOut(
        id=u.id,
        username=u.username,
        real_name=u.real_name,
        email=u.email,
        phone=u.phone,
        department_id=u.department_id,
        department_name=u.department.name if u.department else None,
        avatar_url=u.avatar_url,
        status=u.status,
        role_names=[r.role_name for r in u.roles] if u.roles else [],
        created_at=u.created_at.isoformat() if u.created_at else None,
        updated_at=u.updated_at.isoformat() if u.updated_at else None,
    )


def _department_to_out(d: Department) -> DepartmentOut:
    return DepartmentOut(
        id=d.id,
        name=d.name,
        code=d.code,
        parent_id=d.parent_id,
        created_at=d.created_at.isoformat() if d.created_at else None,
        updated_at=d.updated_at.isoformat() if d.updated_at else None,
    )


# ---------- User Routes ----------

@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    keyword: str = Query(None),
    department: str = Query(None),
    status: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
):
    # Resolve department name to ID if provided
    dept_id = None
    if department:
        dept_result = await db.execute(
            select(Department.id).where(Department.name.ilike(f"%{department}%"))
        )
        dept_id = dept_result.scalar_one_or_none()
        if not dept_id:
            return UserListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    pagination = PaginationParams(page=page, page_size=page_size)
    filters = {}
    if keyword:
        filters["keyword"] = keyword
    if status:
        filters["status"] = status
    if dept_id:
        filters["department_id"] = dept_id

    users, total = await user_service.get_users(db, pagination, filters)

    user_list = [_user_to_out(u) for u in users]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return UserListResponse(
        items=user_list, total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@router.post("/", response_model=UserOut)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
):
    user = await user_service.create_user(db, data)
    # Re-query with eager loads for response
    user = await user_service.get_user(db, user.id)
    return _user_to_out(user)


# ---------- Role Routes ----------
# NOTE: must be defined BEFORE /{user_id} to avoid route matching conflicts

@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cached = await cache.get("users:roles")
    if cached:
        return [RoleOut(**item) for item in cached]

    pagination = PaginationParams(page=1, page_size=500)
    roles, _ = await role_service.get_roles(db, pagination)
    role_list = [RoleOut.model_validate(r) for r in roles]
    await cache.set("users:roles", [r.model_dump() for r in role_list], ttl=600)
    return role_list


@router.post("/roles", response_model=RoleOut)
async def create_role(
    data: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_ROLE_MANAGE)),
):
    role = await role_service.create_role(db, data)
    await cache.delete("users:roles")
    return RoleOut.model_validate(role)


@router.put("/roles/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_ROLE_MANAGE)),
):
    role = await role_service.update_role(db, role_id, data)
    await cache.delete("users:roles")
    return RoleOut.model_validate(role)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_ROLE_MANAGE)),
):
    await role_service.delete_role(db, role_id)
    await cache.delete("users:roles")
    return {"detail": "Role deleted successfully"}


# ---------- Department Routes ----------
# NOTE: must be defined BEFORE /{user_id} to avoid route matching conflicts

@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cached = await cache.get("users:departments")
    if cached:
        return [DepartmentOut(**item) for item in cached]

    pagination = PaginationParams(page=1, page_size=500)
    departments, _ = await department_service.get_departments(db, pagination)
    dept_list = [_department_to_out(d) for d in departments]
    await cache.set("users:departments", [d.model_dump() for d in dept_list], ttl=600)
    return dept_list


@router.get("/departments/tree", response_model=list[DepartmentTreeOut])
async def get_department_tree(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cached = await cache.get("users:departments_tree")
    if cached:
        return [DepartmentTreeOut(**item) for item in cached]

    tree = await department_service.get_department_tree(db)
    roots = [DepartmentTreeOut(**item) for item in tree]
    await cache.set("users:departments_tree", [r.model_dump() for r in roots], ttl=600)
    return roots


@router.post("/departments", response_model=DepartmentOut)
async def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
):
    dept = await department_service.create_department(db, data)
    await cache.delete_pattern("users:departments*")
    return _department_to_out(dept)


@router.put("/departments/{dept_id}", response_model=DepartmentOut)
async def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
):
    dept = await department_service.update_department(db, dept_id, data)
    await cache.delete_pattern("users:departments*")
    return _department_to_out(dept)


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
):
    await department_service.delete_department(db, dept_id)
    await cache.delete_pattern("users:departments*")
    return {"detail": "Department deleted successfully"}


def _category_to_out(c: "DocumentCategory") -> DocumentCategoryOut:
    from app.models.document import DocumentCategory
    return DocumentCategoryOut(
        id=c.id,
        name=c.name,
        code=c.code,
        description=c.description,
        sort_order=c.sort_order,
        is_system=c.is_system,
        created_at=c.created_at.isoformat() if c.created_at else None,
        updated_at=c.updated_at.isoformat() if c.updated_at else None,
    )


def _tag_to_out(t: "Tag") -> TagOut:
    from app.models.document import Tag
    return TagOut(
        id=t.id,
        name=t.name,
        color=t.color,
        created_at=t.created_at.isoformat() if t.created_at else None,
        updated_at=t.updated_at.isoformat() if t.updated_at else None,
    )


# ---------- Document Category Routes ----------

@router.get("/document-categories", response_model=list[DocumentCategoryOut])
async def list_document_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cached = await cache.get("users:document_categories")
    if cached:
        return [DocumentCategoryOut(**item) for item in cached]

    pagination = PaginationParams(page=1, page_size=500)
    categories, _ = await category_service.get_categories(db, pagination)
    cat_list = [_category_to_out(c) for c in categories]
    await cache.set("users:document_categories", [c.model_dump() for c in cat_list], ttl=600)
    return cat_list


@router.post("/document-categories", response_model=DocumentCategoryOut)
async def create_document_category(
    data: DocumentCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_REFDATA_MANAGE)),
):
    category = await category_service.create_category(db, data)
    await cache.delete("users:document_categories")
    return _category_to_out(category)


@router.put("/document-categories/{category_id}", response_model=DocumentCategoryOut)
async def update_document_category(
    category_id: int,
    data: DocumentCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_REFDATA_MANAGE)),
):
    category = await category_service.update_category(db, category_id, data)
    await cache.delete("users:document_categories")
    return _category_to_out(category)


@router.delete("/document-categories/{category_id}")
async def delete_document_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_REFDATA_MANAGE)),
):
    await category_service.delete_category(db, category_id)
    await cache.delete("users:document_categories")
    return {"detail": "Document category deleted successfully"}


# ---------- Tag Routes ----------

@router.get("/tags", response_model=list[TagOut])
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cached = await cache.get("users:tags")
    if cached:
        return [TagOut(**item) for item in cached]

    pagination = PaginationParams(page=1, page_size=500)
    tags, _ = await tag_service.get_tags(db, pagination)
    tag_list = [_tag_to_out(t) for t in tags]
    await cache.set("users:tags", [t.model_dump() for t in tag_list], ttl=600)
    return tag_list


@router.post("/tags", response_model=TagOut)
async def create_tag(
    data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_REFDATA_MANAGE)),
):
    tag = await tag_service.create_tag(db, data)
    await cache.delete("users:tags")
    return _tag_to_out(tag)


@router.put("/tags/{tag_id}", response_model=TagOut)
async def update_tag(
    tag_id: int,
    data: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_REFDATA_MANAGE)),
):
    tag = await tag_service.update_tag(db, tag_id, data)
    await cache.delete("users:tags")
    return _tag_to_out(tag)


@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_REFDATA_MANAGE)),
):
    await tag_service.delete_tag(db, tag_id)
    await cache.delete("users:tags")
    return {"detail": "Tag deleted successfully"}


# ---------- User Detail Routes (/{user_id}) ----------
# These must come AFTER all fixed-path routes above

@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user(db, user_id)
    return _user_to_out(user)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Permission check: admin or self
    is_admin = any(
        hasattr(r, 'role_code') and r.role_code == RoleCode.ADMIN
        for r in (current_user.roles or [])
    )
    is_self = current_user.id == user_id

    if not is_admin and not is_self:
        raise ForbiddenException(detail="You can only update your own profile")

    # Non-admin cannot change roles
    if not is_admin and data.role_ids is not None:
        raise ForbiddenException(detail="Only admins can change roles")

    # Non-admin cannot change department
    if not is_admin and data.department_id is not None:
        raise ForbiddenException(detail="Only admins can change department")

    user = await user_service.update_user(db, user_id, data)
    # Re-query with eager loads for response
    user = await user_service.get_user(db, user.id)
    return _user_to_out(user)


@router.delete("/{user_id}")
async def disable_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_permission(Permission.ADMIN_USER_MANAGE)),
):
    if user_id == current_user.id:
        raise ConflictException(detail="Cannot disable your own account")
    await user_service.delete_user(db, user_id)
    return {"detail": "User disabled successfully"}


@router.put("/{user_id}/password")
async def change_password(
    user_id: int,
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Permission check: admin or self
    is_admin = any(
        hasattr(r, 'role_code') and r.role_code == RoleCode.ADMIN
        for r in (current_user.roles or [])
    )
    is_self = current_user.id == user_id

    if not is_admin and not is_self:
        raise ForbiddenException(detail="You can only change your own password")

    # Admin bypass: admin does not need old password
    if is_admin and not is_self:
        # Admin resetting another user's password
        user = await user_service._get_user_basic(db, user_id)
        user.password_hash = hash_password(data.new_password)
        await db.commit()
        return {"detail": "Password changed successfully"}

    # Self or admin changing own password: must verify old password
    user = await user_service._get_user_basic(db, user_id)
    if not verify_password(data.old_password, user.password_hash):
        raise ForbiddenException(detail="Old password is incorrect")

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"detail": "Password changed successfully"}

