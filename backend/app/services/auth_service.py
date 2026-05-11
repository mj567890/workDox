import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.core.security import verify_password, hash_password, create_access_token, create_reset_token, decode_reset_token
from app.core.exceptions import UnauthorizedException, NotFoundException

logger = logging.getLogger(__name__)


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

        if not user:
            logger.warning("Failed login attempt: user '%s' not found or disabled", username)
            raise UnauthorizedException(detail="Invalid username or password")
        if user.auth_provider != "local":
            logger.warning("Failed login attempt: user '%s' uses %s auth", username, user.auth_provider)
            raise UnauthorizedException(detail=f"This account uses {user.auth_provider} authentication. Please use the appropriate login method.")
        if not verify_password(password, user.password_hash):
            logger.warning("Failed login attempt: incorrect password for user '%s'", username)
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

    async def forgot_password(
        self, db: AsyncSession, email: str, reset_url_base: str
    ) -> bool:
        """Process forgot-password: generate token, store hash, send email.

        Returns:
            True  = email sent successfully → show generic success
            False = user not found → show generic success (anti-enumeration)
        Raises on email send failure so the API can return an error.
        """
        from app.config import get_settings
        from app.utils.email_sender import email_sender

        settings = get_settings()

        stmt = select(User).where(
            User.email == email,
            User.status == "active",
            User.auth_provider == "local",
        )
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            logger.info("Forgot-password for unknown/disallowed email: %s", email)
            return False

        token = create_reset_token(user.id)
        user.reset_token_hash = hash_password(token)
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
        )
        await db.commit()

        reset_url = f"{reset_url_base}?token={token}"
        sent = await email_sender.send(
            to_email=email,
            template_name="reset_password",
            context={
                "username": user.username,
                "reset_url": reset_url,
                "expire_minutes": settings.RESET_TOKEN_EXPIRE_MINUTES,
            },
        )

        if not sent:
            # Roll back the token so no dangling reset token exists
            user.reset_token_hash = None
            user.reset_token_expires = None
            await db.commit()
            logger.warning("Password reset email FAILED for user_id=%d email=%s", user.id, email)
            raise Exception("邮件发送失败，请检查 SMTP 配置或稍后重试")

        logger.info("Password reset email sent to user_id=%d email=%s", user.id, email)
        return True

    async def _verify_reset_token(self, db: AsyncSession, token: str) -> User:
        """Validate a reset token and return the user. Raises on any failure."""
        payload = decode_reset_token(token)
        if not payload:
            raise UnauthorizedException(detail="Invalid or expired reset token")

        user_id = int(payload["sub"])

        stmt = select(User).where(User.id == user_id, User.status == "active")
        result = await db.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise UnauthorizedException(detail="Invalid or expired reset token")

        if user.auth_provider != "local":
            raise UnauthorizedException(detail="Password reset is only available for local accounts")

        if user.reset_token_hash is None or user.reset_token_expires is None:
            raise UnauthorizedException(detail="Invalid or expired reset token")

        if user.reset_token_expires < datetime.now(timezone.utc):
            user.reset_token_hash = None
            user.reset_token_expires = None
            await db.commit()
            raise UnauthorizedException(detail="Reset token has expired")

        if not verify_password(token, user.reset_token_hash):
            raise UnauthorizedException(detail="Invalid reset token")

        return user

    async def reset_password(
        self, db: AsyncSession, token: str, new_password: str
    ) -> None:
        """Reset a user's password using a valid reset token."""
        user = await self._verify_reset_token(db, token)

        user.password_hash = hash_password(new_password)
        user.reset_token_hash = None
        user.reset_token_expires = None
        await db.commit()
        logger.info("Password reset completed for user_id=%d", user.id)
