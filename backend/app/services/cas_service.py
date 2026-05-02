import secrets
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.security import create_access_token
from app.core.exceptions import UnauthorizedException, AppException
from app.models.user import User
from app.models.role import Role


class CasService:
    """CAS 2.0 / CAS 3.0 protocol authentication.

    Flow:
    1. GET /auth/sso/cas/authorize → redirect to CAS /login?service=<callback>
    2. CAS authenticates user → redirects back to callback with ?ticket=ST-xxx
    3. GET /auth/sso/cas/callback → POST ticket to CAS /serviceValidate
    4. CAS returns XML with user attributes → find/create user → issue JWT
    5. Redirect to frontend with token
    """

    def get_authorize_url(self) -> tuple[str, str | None]:
        settings = get_settings()
        if not settings.CAS_ENABLED:
            raise AppException(detail="CAS authentication is not enabled")

        # CAS spec: add a random parameter to prevent ticket reuse
        # Not strictly required but good practice
        login_url = f"{settings.CAS_SERVER_URL}{settings.CAS_LOGIN_URL}"
        params = {"service": self._service_url()}
        auth_url = f"{login_url}?{urlencode(params)}"
        return auth_url, None

    async def validate_ticket(self, db: AsyncSession, ticket: str) -> dict:
        """Validate CAS ticket and authenticate user.

        Uses CAS 2.0 /serviceValidate endpoint (returns user attributes).
        Falls back gracefully if CAS 3.0 attributes are not present.
        """
        settings = get_settings()
        if not settings.CAS_ENABLED:
            raise UnauthorizedException(detail="CAS authentication is not enabled")

        validate_url = f"{settings.CAS_SERVER_URL}{settings.CAS_VALIDATE_URL}"
        params = {"service": self._service_url(), "ticket": ticket}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(validate_url, params=params)
            if resp.status_code != 200:
                raise UnauthorizedException(
                    detail=f"CAS ticket validation failed: HTTP {resp.status_code}"
                )

        # Parse CAS XML response
        user_attrs = self._parse_cas_response(resp.text)

        if user_attrs is None:
            raise UnauthorizedException(detail="CAS ticket validation failed: invalid ticket or service")

        username = user_attrs.get("user") or user_attrs.get("uid") or user_attrs.get("username", "")
        real_name = user_attrs.get("cn") or user_attrs.get("name") or user_attrs.get("displayName", username)
        email = user_attrs.get("mail") or user_attrs.get("email")

        if not username:
            raise UnauthorizedException(detail="CAS response missing user identifier")

        # Find or create local user
        user = await self._find_or_create_cas_user(db, username, real_name, email)

        # Fetch roles
        roles_result = await db.execute(
            select(Role).join(Role.users).where(User.id == user.id)
        )
        role_list = list(roles_result.scalars().all())

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

    def _parse_cas_response(self, xml_text: str) -> dict | None:
        """Parse CAS 2.0/3.0 serviceValidate XML response.

        CAS 2.0 success response:
        <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
          <cas:authenticationSuccess>
            <cas:user>username</cas:user>
            <cas:attributes>
              ...
            </cas:attributes>
          </cas:authenticationSuccess>
        </cas:serviceResponse>

        CAS 2.0 failure response:
        <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
          <cas:authenticationFailure code="INVALID_TICKET">
            Ticket not recognized
          </cas:authenticationFailure>
        </cas:serviceResponse>
        """
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError:
            return None

        # CAS namespace
        ns = "http://www.yale.edu/tp/cas"

        # Check for authentication failure
        failure = root.find(f"{{{ns}}}authenticationFailure")
        if failure is not None:
            return None  # Ticket invalid

        # Parse success
        success = root.find(f"{{{ns}}}authenticationSuccess")
        if success is None:
            return None

        user_el = success.find(f"{{{ns}}}user")
        if user_el is None:
            return None

        result = {"user": user_el.text.strip() if user_el.text else ""}

        # Parse CAS attributes (both CAS 2.0 and CAS 3.0 format)
        # CAS 3.0 uses <cas:attributes> block
        attrs_block = success.find(f"{{{ns}}}attributes")
        if attrs_block is None:
            # CAS 2.0 may have flat attributes directly
            # Some CAS servers use cas: prefix for attributes inside success
            pass

        # Extract any additional attributes
        for child in success:
            tag = child.tag.replace(f"{{{ns}}}", "")
            if tag not in ("user", "attributes", "proxyGrantingTicket"):
                result[tag] = child.text.strip() if child.text else ""
            elif tag == "attributes" and attrs_block is not None:
                for attr in attrs_block:
                    attr_name = attr.tag.replace(f"{{{ns}}}", "")
                    result[attr_name] = attr.text.strip() if attr.text else ""

        return result

    async def _find_or_create_cas_user(
        self, db: AsyncSession, username: str, real_name: str,
        email: str | None,
    ) -> User:
        settings = get_settings()

        # Try by username first
        stmt = select(User).options(selectinload(User.roles)).where(
            User.username == username
        )
        result = await db.execute(stmt)
        user = result.scalars().first()

        if user:
            # Update auth provider if needed
            if user.auth_provider == "local":
                user.auth_provider = "cas"
                user.real_name = real_name or user.real_name
                user.email = email or user.email
                await db.commit()
                await db.refresh(user)
            return user

        # Try by email
        if email:
            stmt = select(User).options(selectinload(User.roles)).where(
                User.email == email
            )
            result = await db.execute(stmt)
            user = result.scalars().first()
            if user:
                user.auth_provider = "cas"
                if user.username != username:
                    user.oauth_subject = f"cas:{username}"
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
            auth_provider="cas",
            status="active",
        )
        if default_role:
            user.roles.append(default_role)

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    def _service_url(self) -> str:
        return get_settings().CAS_REDIRECT_URI or "http://localhost:8000/api/v1/auth/sso/cas/callback"
