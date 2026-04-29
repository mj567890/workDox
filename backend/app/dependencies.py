from typing import AsyncGenerator, Optional

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import get_settings
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.permissions import Permission

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _get_async_session_factory():
    """Return the async session factory for use in background tasks."""
    return async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException()

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedException(detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException()

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.user import User

    result = await db.execute(
        select(User).options(selectinload(User.roles), selectinload(User.department)).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    if not user or user.status != "active":
        raise UnauthorizedException(detail="User not found or disabled")

    return user


class PermissionChecker:
    def __init__(self, permission: Permission):
        self.permission = permission

    async def __call__(self, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        from sqlalchemy import select
        from app.models.role import Role
        from app.core.permissions import has_permission

        result = await db.execute(
            select(Role).where(
                Role.id.in_(
                    select(Role.id).join(
                        Role.users.property.secondary if hasattr(Role.users.property, 'secondary') else None
                    )
                )
            )
        )
        # Simplified: check user's roles
        user_roles = await db.execute(
            select(Role).where(
                Role.id.in_(
                    # subquery to get role ids from user_role
                    select(Role.__table__.c.id)
                    .select_from(Role.__table__)
                    .join(Role.users.property.secondary if hasattr(Role.users.property, 'secondary') else None)
                )
            )
        )


def check_permission(permission: Permission):
    async def _check(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        from sqlalchemy import select
        from app.models.role import Role
        from app.models.user import user_role
        from app.core.permissions import has_permission, RoleCode

        result = await db.execute(
            select(Role.role_code).join(user_role).where(user_role.c.user_id == current_user.id)
        )
        role_codes = [row[0] for row in result.all()]

        for code in role_codes:
            try:
                if has_permission(RoleCode(code), permission):
                    return
            except ValueError:
                continue

        raise ForbiddenException(detail=f"Missing permission: {permission}")
    return _check
