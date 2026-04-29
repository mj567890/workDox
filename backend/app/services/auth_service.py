from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.core.exceptions import UnauthorizedException, NotFoundException


class AuthService:

    async def authenticate(
        self, db: AsyncSession, username: str, password: str
    ) -> dict:
        stmt = (
            select(User)
            .options(selectinload(User.roles), selectinload(User.department))
            .where(User.username == username, User.status == "active")
        )
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException(detail="Invalid username or password")

        roles = [
            {"id": role.id, "role_name": role.role_name, "role_code": role.role_code}
            for role in user.roles
        ]

        department_info = None
        if user.department:
            department_info = {
                "id": user.department.id,
                "name": user.department.name,
                "code": user.department.code,
            }

        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "real_name": user.real_name,
            "roles": [role.role_code for role in user.roles],
        }
        access_token = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "real_name": user.real_name,
                "email": user.email,
                "phone": user.phone,
                "department": department_info,
                "roles": roles,
                "avatar_url": user.avatar_url,
            },
        }

    async def get_current_user_info(
        self, db: AsyncSession, user_id: int
    ) -> dict:
        stmt = (
            select(User)
            .options(selectinload(User.roles), selectinload(User.department))
            .where(User.id == user_id, User.status == "active")
        )
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise NotFoundException(resource="User")

        roles = [
            {
                "id": role.id,
                "role_name": role.role_name,
                "role_code": role.role_code,
            }
            for role in user.roles
        ]

        department_info = None
        if user.department:
            department_info = {
                "id": user.department.id,
                "name": user.department.name,
                "code": user.department.code,
            }

        return {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "email": user.email,
            "phone": user.phone,
            "department": department_info,
            "roles": roles,
            "avatar_url": user.avatar_url,
            "status": user.status,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
