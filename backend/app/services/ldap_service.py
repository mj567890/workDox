from ldap3 import Server, Connection, ALL, SUBTREE
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.security import create_access_token
from app.core.exceptions import UnauthorizedException
from app.models.user import User
from app.models.role import Role


class LdapService:

    async def authenticate(self, db: AsyncSession, username: str, password: str) -> dict:
        settings = get_settings()

        if not settings.LDAP_ENABLED:
            raise UnauthorizedException(detail="LDAP authentication is not enabled")

        user_dn = settings.LDAP_USER_DN_TEMPLATE.format(username=username)

        server = Server(settings.LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user_dn, password, auto_bind=True)

        try:
            # Search for user attributes
            conn.search(
                search_base=settings.LDAP_BASE_DN,
                search_filter=f"(&(objectClass=person)(sAMAccountName={username}))",
                search_scope=SUBTREE,
                attributes=[settings.LDAP_ATTR_REAL_NAME, settings.LDAP_ATTR_EMAIL, settings.LDAP_ATTR_PHONE],
            )

            real_name = username
            email = None
            phone = None

            if conn.entries:
                entry = conn.entries[0]
                real_name = getattr(entry, settings.LDAP_ATTR_REAL_NAME, None)
                if real_name and hasattr(real_name, 'value'):
                    real_name = real_name.value or username
                elif not real_name:
                    real_name = username

                email_attr = getattr(entry, settings.LDAP_ATTR_EMAIL, None)
                if email_attr:
                    email = email_attr.value if hasattr(email_attr, 'value') else str(email_attr)

                phone_attr = getattr(entry, settings.LDAP_ATTR_PHONE, None)
                if phone_attr:
                    phone = phone_attr.value if hasattr(phone_attr, 'value') else str(phone_attr)
        finally:
            conn.unbind()

        user = await self._find_or_create_user(db, username, real_name, email, phone, provider="ldap")

        roles = await db.execute(
            select(Role).join(Role.users).where(User.id == user.id)
        )
        role_list = [r for r in roles.scalars().all()]

        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "real_name": user.real_name,
            "roles": [r.role_code for r in role_list],
        }
        access_token = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "real_name": user.real_name,
        }

    async def _find_or_create_user(
        self, db: AsyncSession, username: str, real_name: str,
        email: str | None, phone: str | None, provider: str,
    ) -> User:
        # Match by username first
        stmt = select(User).options(selectinload(User.roles)).where(User.username == username)
        result = await db.execute(stmt)
        user = result.scalars().first()

        if user:
            # Update auth_provider if migrating from local
            if user.auth_provider == "local":
                user.auth_provider = provider
                user.real_name = real_name
                user.email = email or user.email
                user.phone = phone or user.phone
                await db.commit()
                await db.refresh(user)
            return user

        # Match by email for SSO users
        if email:
            stmt = select(User).options(selectinload(User.roles)).where(User.email == email)
            result = await db.execute(stmt)
            user = result.scalars().first()
            if user:
                user.auth_provider = provider
                await db.commit()
                await db.refresh(user)
                return user

        # Create new user
        general_staff = await db.execute(
            select(Role).where(Role.role_code == "general_staff")
        )
        default_role = general_staff.scalars().first()

        user = User(
            username=username,
            password_hash="",  # External auth — no local password
            real_name=real_name,
            email=email,
            phone=phone,
            auth_provider=provider,
            status="active",
        )
        if default_role:
            user.roles.append(default_role)

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
