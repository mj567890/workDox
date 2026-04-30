import secrets
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.security import create_access_token
from app.core.exceptions import UnauthorizedException, AppException
from app.models.user import User
from app.models.role import Role


class OAuth2Service:

    def get_provider_info(self) -> dict:
        settings = get_settings()
        return {
            "enabled": settings.OAUTH2_ENABLED,
            "provider_name": settings.OAUTH2_PROVIDER_NAME,
        }

    def get_authorize_url(self) -> tuple[str, str]:
        settings = get_settings()
        if not settings.OAUTH2_ENABLED:
            raise AppException(detail="OAuth2 is not enabled")

        state = secrets.token_urlsafe(32)

        from app.core.security import create_access_token
        from datetime import timedelta
        state_token = create_access_token({"state": state, "purpose": "oauth2"}, expires_delta=timedelta(minutes=5))

        params = {
            "client_id": settings.OAUTH2_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": self._redirect_uri(),
            "scope": settings.OAUTH2_SCOPES,
            "state": state_token,
        }
        auth_url = f"{settings.OAUTH2_AUTHORIZE_URL}?{urlencode(params)}"
        return auth_url, state_token

    async def handle_callback(self, db: AsyncSession, code: str, state: str) -> dict:
        settings = get_settings()

        # Validate state token
        from app.core.security import decode_access_token
        payload = decode_access_token(state)
        if not payload or payload.get("purpose") != "oauth2":
            raise UnauthorizedException(detail="Invalid OAuth2 state parameter")

        # Exchange code for tokens
        token_url = settings.OAUTH2_TOKEN_URL
        async with httpx.AsyncClient(timeout=30) as client:
            token_resp = await client.post(token_url, data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._redirect_uri(),
                "client_id": settings.OAUTH2_CLIENT_ID,
                "client_secret": settings.OAUTH2_CLIENT_SECRET,
            })
            if token_resp.status_code != 200:
                raise UnauthorizedException(detail=f"Token exchange failed: {token_resp.text[:200]}")
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise UnauthorizedException(detail="No access_token in token response")

            # Fetch userinfo
            userinfo_url = settings.OAUTH2_USERINFO_URL
            userinfo_resp = await client.get(userinfo_url, headers={
                "Authorization": f"Bearer {access_token}",
            })
            if userinfo_resp.status_code != 200:
                raise UnauthorizedException(detail=f"Userinfo request failed: {userinfo_resp.text[:200]}")
            userinfo = userinfo_resp.json()

        # Extract user identity
        username = userinfo.get(settings.OAUTH2_USERNAME_CLAIM, "")
        name = userinfo.get(settings.OAUTH2_NAME_CLAIM, username)
        email = userinfo.get(settings.OAUTH2_EMAIL_CLAIM)
        sub = userinfo.get(settings.OAUTH2_USER_ID_CLAIM, username)

        if not username:
            username = sub

        # Find by oauth_subject first, then username, then email
        user = await self._find_or_create_oauth_user(db, username, name, email, sub)

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
        jwt_token = create_access_token(token_data)

        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "real_name": user.real_name,
        }

    async def _find_or_create_oauth_user(
        self, db: AsyncSession, username: str, real_name: str,
        email: str | None, sub: str,
    ) -> User:
        settings = get_settings()

        # Try oauth_subject
        stmt = select(User).options(selectinload(User.roles)).where(User.oauth_subject == sub)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user:
            return user

        # Try email
        if email:
            stmt = select(User).options(selectinload(User.roles)).where(User.email == email)
            result = await db.execute(stmt)
            user = result.scalars().first()
            if user:
                user.oauth_provider = settings.OAUTH2_PROVIDER_NAME
                user.oauth_subject = sub
                if user.auth_provider == "local":
                    user.auth_provider = "oauth2"
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
            password_hash="",
            real_name=real_name,
            email=email,
            auth_provider="oauth2",
            oauth_provider=settings.OAUTH2_PROVIDER_NAME,
            oauth_subject=sub,
            status="active",
        )
        if default_role:
            user.roles.append(default_role)

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    def _redirect_uri(self) -> str:
        return get_settings().OAUTH2_REDIRECT_URI or "http://localhost:8000/api/v1/auth/oauth2/callback"
