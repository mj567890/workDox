from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.role import Role
from app.models.department import Department
from app.models.document import DocumentCategory, Tag, Document

from app.core.security import hash_password, verify_password
from app.core.pagination import PaginationParams
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    ValidationException,
    ForbiddenException,
)


class UserService:

    async def create_user(self, db: AsyncSession, data: "UserCreate") -> User:
        existing = await db.execute(
            select(User).where(User.username == data.username)
        )
        if existing.scalars().first():
            raise ConflictException(detail=f"Username '{data.username}' already exists")

        if data.email:
            existing_email = await db.execute(
                select(User).where(User.email == data.email)
            )
            if existing_email.scalars().first():
                raise ConflictException(detail=f"Email '{data.email}' already in use")

        user = User(
            username=data.username,
            password_hash=hash_password(data.password),
            real_name=data.real_name,
            email=data.email,
            phone=data.phone,
            department_id=data.department_id,
            status="active",
            avatar_url=data.avatar_url,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        if data.role_ids:
            await self._assign_roles(db, user, data.role_ids)

        return user

    async def get_user(self, db: AsyncSession, user_id: int) -> User:
        stmt = (
            select(User)
            .options(selectinload(User.roles), selectinload(User.department))
            .where(User.id == user_id)
        )
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise NotFoundException(resource="User")
        return user

    async def get_users(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        filters: dict,
    ) -> tuple[list[User], int]:
        conditions = []

        if filters.get("status"):
            conditions.append(User.status == filters["status"])
        if filters.get("department_id"):
            conditions.append(User.department_id == filters["department_id"])
        if filters.get("keyword"):
            kw = f"%{filters['keyword']}%"
            conditions.append(
                or_(
                    User.username.ilike(kw),
                    User.real_name.ilike(kw),
                    User.email.ilike(kw),
                )
            )
        if filters.get("role_id"):
            conditions.append(
                User.id.in_(
                    select(User.id).join(User.roles).where(Role.id == filters["role_id"])
                )
            )

        base_query = (
            select(User)
            .options(selectinload(User.roles), selectinload(User.department))
        )
        if conditions:
            base_query = base_query.where(and_(*conditions))

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(User.id.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def update_user(
        self, db: AsyncSession, user_id: int, data: "UserUpdate"
    ) -> User:
        user = await self.get_user(db, user_id)

        update_data = data.model_dump(exclude_unset=True)

        if "password" in update_data:
            update_data["password_hash"] = hash_password(update_data.pop("password"))

        if "role_ids" in update_data:
            role_ids = update_data.pop("role_ids")
            await self._assign_roles(db, user, role_ids)

        for key, value in update_data.items():
            if hasattr(user, key) and key not in ("id", "password", "password_hash"):
                setattr(user, key, value)

        await db.commit()
        await db.refresh(user)
        return user

    async def delete_user(self, db: AsyncSession, user_id: int) -> bool:
        user = await self.get_user(db, user_id)
        user.status = "disabled"
        await db.commit()
        await db.refresh(user)
        return True

    async def change_password(
        self, db: AsyncSession, user_id: int, old_password: str, new_password: str
    ) -> bool:
        user = await self._get_user_basic(db, user_id)

        if not verify_password(old_password, user.password_hash):
            raise ValidationException(detail="Old password is incorrect")

        if old_password == new_password:
            raise ValidationException(
                detail="New password must be different from old password"
            )

        user.password_hash = hash_password(new_password)
        await db.commit()
        return True

    async def _get_user_basic(self, db: AsyncSession, user_id: int) -> User:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if not user:
            raise NotFoundException(resource="User")
        return user

    async def _assign_roles(
        self, db: AsyncSession, user: User, role_ids: list[int]
    ) -> None:
        roles_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
        roles = roles_result.scalars().all()

        if len(roles) != len(role_ids):
            found_ids = {role.id for role in roles}
            missing = set(role_ids) - found_ids
            raise NotFoundException(resource=f"Role(s): {missing}")

        user.roles = list(roles)
        await db.commit()


class RoleService:

    async def create_role(self, db: AsyncSession, data: "RoleCreate") -> Role:
        existing = await db.execute(
            select(Role).where(Role.role_code == data.role_code)
        )
        if existing.scalars().first():
            raise ConflictException(
                detail=f"Role code '{data.role_code}' already exists"
            )

        role = Role(
            role_name=data.role_name,
            role_code=data.role_code,
            description=data.description,
        )
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role

    async def get_role(self, db: AsyncSession, role_id: int) -> Role:
        stmt = select(Role).where(Role.id == role_id)
        result = await db.execute(stmt)
        role = result.scalars().first()
        if not role:
            raise NotFoundException(resource="Role")
        return role

    async def get_roles(
        self, db: AsyncSession, pagination: PaginationParams
    ) -> tuple[list[Role], int]:
        base_query = select(Role)

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(Role.id)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def update_role(
        self, db: AsyncSession, role_id: int, data: "RoleUpdate"
    ) -> Role:
        role = await self.get_role(db, role_id)

        update_data = data.model_dump(exclude_unset=True)

        if "role_code" in update_data:
            existing = await db.execute(
                select(Role).where(
                    Role.role_code == update_data["role_code"],
                    Role.id != role_id,
                )
            )
            if existing.scalars().first():
                raise ConflictException(
                    detail=f"Role code '{update_data['role_code']}' already exists"
                )

        for key, value in update_data.items():
            if hasattr(role, key) and key != "id":
                setattr(role, key, value)

        await db.commit()
        await db.refresh(role)
        return role

    async def delete_role(self, db: AsyncSession, role_id: int) -> bool:
        role = await self.get_role(db, role_id)
        await db.delete(role)
        await db.commit()
        return True


class DepartmentService:

    async def create_department(
        self, db: AsyncSession, data: "DepartmentCreate"
    ) -> Department:
        existing = await db.execute(
            select(Department).where(Department.code == data.code)
        )
        if existing.scalars().first():
            raise ConflictException(
                detail=f"Department code '{data.code}' already exists"
            )

        if data.parent_id:
            parent = await db.execute(
                select(Department).where(Department.id == data.parent_id)
            )
            if not parent.scalars().first():
                raise NotFoundException(resource="Parent department")

        dept = Department(
            name=data.name,
            code=data.code,
            parent_id=data.parent_id,
        )
        db.add(dept)
        await db.commit()
        await db.refresh(dept)
        return dept

    async def get_department(
        self, db: AsyncSession, dept_id: int
    ) -> Department:
        stmt = select(Department).where(Department.id == dept_id)
        result = await db.execute(stmt)
        dept = result.scalars().first()
        if not dept:
            raise NotFoundException(resource="Department")
        return dept

    async def get_departments(
        self, db: AsyncSession, pagination: PaginationParams
    ) -> tuple[list[Department], int]:
        base_query = select(Department)

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(Department.id)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def get_department_tree(
        self, db: AsyncSession
    ) -> list[dict]:
        stmt = select(Department).order_by(Department.id)
        result = await db.execute(stmt)
        all_depts = result.scalars().all()

        dept_map: dict[int, dict] = {}
        tree: list[dict] = []

        for dept in all_depts:
            node = {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "parent_id": dept.parent_id,
                "children": [],
            }
            dept_map[dept.id] = node

        for dept in all_depts:
            node = dept_map[dept.id]
            if dept.parent_id and dept.parent_id in dept_map:
                dept_map[dept.parent_id]["children"].append(node)
            else:
                tree.append(node)

        return tree

    async def update_department(
        self, db: AsyncSession, dept_id: int, data: "DepartmentUpdate"
    ) -> Department:
        dept = await self.get_department(db, dept_id)

        update_data = data.model_dump(exclude_unset=True)

        if "code" in update_data:
            existing = await db.execute(
                select(Department).where(
                    Department.code == update_data["code"],
                    Department.id != dept_id,
                )
            )
            if existing.scalars().first():
                raise ConflictException(
                    detail=f"Department code '{update_data['code']}' already exists"
                )

        if "parent_id" in update_data and update_data["parent_id"]:
            if update_data["parent_id"] == dept_id:
                raise ValidationException(
                    detail="Department cannot be its own parent"
                )
            parent = await db.execute(
                select(Department).where(
                    Department.id == update_data["parent_id"]
                )
            )
            if not parent.scalars().first():
                raise NotFoundException(resource="Parent department")

        for key, value in update_data.items():
            if hasattr(dept, key) and key != "id":
                setattr(dept, key, value)

        await db.commit()
        await db.refresh(dept)
        return dept

    async def delete_department(self, db: AsyncSession, dept_id: int) -> bool:
        dept = await self.get_department(db, dept_id)

        children_result = await db.execute(
            select(Department).where(Department.parent_id == dept_id)
        )
        if children_result.scalars().first():
            raise ConflictException(
                detail="Cannot delete department with child departments"
            )

        users_result = await db.execute(
            select(User).where(User.department_id == dept_id)
        )
        if users_result.scalars().first():
            raise ConflictException(
                detail="Cannot delete department with assigned users"
            )

        await db.delete(dept)
        await db.commit()
        return True


class DocumentCategoryService:

    async def create_category(self, db: AsyncSession, data: "DocumentCategoryCreate") -> DocumentCategory:
        existing = await db.execute(
            select(DocumentCategory).where(DocumentCategory.code == data.code)
        )
        if existing.scalars().first():
            raise ConflictException(
                detail=f"Category code '{data.code}' already exists"
            )

        category = DocumentCategory(
            name=data.name,
            code=data.code,
            description=data.description,
            sort_order=data.sort_order,
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    async def get_category(self, db: AsyncSession, category_id: int) -> DocumentCategory:
        stmt = select(DocumentCategory).where(DocumentCategory.id == category_id)
        result = await db.execute(stmt)
        category = result.scalars().first()
        if not category:
            raise NotFoundException(resource="DocumentCategory")
        return category

    async def get_categories(
        self, db: AsyncSession, pagination: PaginationParams
    ) -> tuple[list[DocumentCategory], int]:
        base_query = select(DocumentCategory)

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(DocumentCategory.sort_order, DocumentCategory.id)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def update_category(
        self, db: AsyncSession, category_id: int, data: "DocumentCategoryUpdate"
    ) -> DocumentCategory:
        category = await self.get_category(db, category_id)

        update_data = data.model_dump(exclude_unset=True)

        if "code" in update_data:
            existing = await db.execute(
                select(DocumentCategory).where(
                    DocumentCategory.code == update_data["code"],
                    DocumentCategory.id != category_id,
                )
            )
            if existing.scalars().first():
                raise ConflictException(
                    detail=f"Category code '{update_data['code']}' already exists"
                )

        for key, value in update_data.items():
            if hasattr(category, key) and key not in ("id", "is_system"):
                setattr(category, key, value)

        await db.commit()
        await db.refresh(category)
        return category

    async def delete_category(self, db: AsyncSession, category_id: int) -> bool:
        category = await self.get_category(db, category_id)

        if category.is_system:
            raise ConflictException(
                detail="Cannot delete system category"
            )

        docs_result = await db.execute(
            select(Document).where(Document.category_id == category_id)
        )
        if docs_result.scalars().first():
            raise ConflictException(
                detail="Cannot delete category with assigned documents"
            )

        await db.delete(category)
        await db.commit()
        return True


class TagService:

    async def create_tag(self, db: AsyncSession, data: "TagCreate") -> Tag:
        existing = await db.execute(
            select(Tag).where(Tag.name == data.name)
        )
        if existing.scalars().first():
            raise ConflictException(
                detail=f"Tag name '{data.name}' already exists"
            )

        tag = Tag(
            name=data.name,
            color=data.color,
        )
        db.add(tag)
        await db.commit()
        await db.refresh(tag)
        return tag

    async def get_tag(self, db: AsyncSession, tag_id: int) -> Tag:
        stmt = select(Tag).where(Tag.id == tag_id)
        result = await db.execute(stmt)
        tag = result.scalars().first()
        if not tag:
            raise NotFoundException(resource="Tag")
        return tag

    async def get_tags(
        self, db: AsyncSession, pagination: PaginationParams
    ) -> tuple[list[Tag], int]:
        base_query = select(Tag)

        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        stmt = (
            base_query
            .order_by(Tag.id)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await db.execute(stmt)
        items = result.scalars().all()

        return list(items), total

    async def update_tag(
        self, db: AsyncSession, tag_id: int, data: "TagUpdate"
    ) -> Tag:
        tag = await self.get_tag(db, tag_id)

        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            existing = await db.execute(
                select(Tag).where(
                    Tag.name == update_data["name"],
                    Tag.id != tag_id,
                )
            )
            if existing.scalars().first():
                raise ConflictException(
                    detail=f"Tag name '{update_data['name']}' already exists"
                )

        for key, value in update_data.items():
            if hasattr(tag, key) and key != "id":
                setattr(tag, key, value)

        await db.commit()
        await db.refresh(tag)
        return tag

    async def delete_tag(self, db: AsyncSession, tag_id: int) -> bool:
        tag = await self.get_tag(db, tag_id)

        from app.models.document import DocumentTag
        refs_result = await db.execute(
            select(DocumentTag).where(DocumentTag.tag_id == tag_id)
        )
        if refs_result.scalars().first():
            raise ConflictException(
                detail="Cannot delete tag that is assigned to documents"
            )

        await db.delete(tag)
        await db.commit()
        return True
