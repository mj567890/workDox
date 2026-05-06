import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.limiter import limiter
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.ldap_service import LdapService
from app.services.oauth2_service import OAuth2Service
from app.services.cas_service import CasService

router = APIRouter()
logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    real_name: str


class RoleBrief(BaseModel):
    id: int
    role_name: str
    role_code: str


class UserInfoResponse(BaseModel):
    id: int
    username: str
    real_name: str
    email: str | None
    phone: str | None
    department_id: int | None
    department_name: str | None
    avatar_url: str | None
    status: str
    roles: list[RoleBrief]

    class Config:
        from_attributes = True


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    result = await AuthService().authenticate(db, body.username, body.password)
    user = result["user"]
    logger.info("User login: username=%s user_id=%d ip=%s", user["username"], user["id"], client_ip)
    return TokenResponse(
        access_token=result["access_token"],
        token_type=result.get("token_type", "bearer"),
        user_id=user["id"],
        username=user["username"],
        real_name=user["real_name"],
    )


@router.post("/logout")
@limiter.limit("10/minute")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    return {"detail": "Logged out successfully"}


@router.get("/providers")
async def get_providers():
    settings = get_settings()
    providers = ["local"]
    if settings.LDAP_ENABLED:
        providers.append("ldap")
    if settings.CAS_ENABLED:
        providers.append({"name": settings.CAS_PROVIDER_NAME, "type": "cas"})
    if settings.OAUTH2_ENABLED:
        providers.append({"name": settings.OAUTH2_PROVIDER_NAME, "type": "oauth2"})
    return {"providers": providers}


@router.post("/ldap/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def ldap_login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await LdapService().authenticate(db, body.username, body.password)
    return TokenResponse(
        access_token=result["access_token"],
        token_type=result.get("token_type", "bearer"),
        user_id=result["user_id"],
        username=result["username"],
        real_name=result["real_name"],
    )


# ── CAS / 高校统一认证 ──────────────────────────────────────────


@router.get("/sso/cas/authorize")
async def cas_authorize():
    """Redirect to CAS server login page."""
    service = CasService()
    auth_url, _ = service.get_authorize_url()
    return RedirectResponse(url=auth_url)


@router.get("/sso/cas/callback")
@limiter.limit("10/minute")
async def cas_callback(
    request: Request,
    ticket: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """CAS ticket validation callback.

    CAS server redirects here after successful authentication.
    Validates ticket and returns JWT to frontend.
    """
    service = CasService()
    result = await service.validate_ticket(db, ticket)
    settings = get_settings()
    frontend_url = settings.CORS_ORIGINS[0]
    return RedirectResponse(
        url=f"{frontend_url}/auth/cas/callback?token={result['access_token']}"
    )


# ── OAuth2 / OIDC ──────────────────────────────────────────────


@router.get("/oauth2/authorize")
async def oauth2_authorize():
    service = OAuth2Service()
    auth_url, _ = service.get_authorize_url()
    return RedirectResponse(url=auth_url)


@router.get("/oauth2/callback")
@limiter.limit("10/minute")
async def oauth2_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    service = OAuth2Service()
    result = await service.handle_callback(db, code, state)
    settings = get_settings()
    frontend_url = settings.CORS_ORIGINS[0]
    return RedirectResponse(
        url=f"{frontend_url}/auth/oauth2/callback?token={result['access_token']}"
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await AuthService().get_current_user_info(db, current_user.id)
    dept = result.get("department")
    return UserInfoResponse(
        id=result["id"],
        username=result["username"],
        real_name=result["real_name"],
        email=result["email"],
        phone=result["phone"],
        department_id=dept["id"] if dept else None,
        department_name=dept["name"] if dept else None,
        avatar_url=result["avatar_url"],
        status=result["status"],
        roles=[
            RoleBrief(id=r["id"], role_name=r["role_name"], role_code=r["role_code"])
            for r in result["roles"]
        ],
    )
