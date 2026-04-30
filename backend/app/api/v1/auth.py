from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.ldap_service import LdapService
from app.services.oauth2_service import OAuth2Service

router = APIRouter()


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
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await AuthService().authenticate(db, request.username, request.password)
    user = result["user"]
    return TokenResponse(
        access_token=result["access_token"],
        token_type=result.get("token_type", "bearer"),
        user_id=user["id"],
        username=user["username"],
        real_name=user["real_name"],
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"detail": "Logged out successfully"}


@router.get("/providers")
async def get_providers():
    settings = get_settings()
    providers = ["local"]
    if settings.LDAP_ENABLED:
        providers.append("ldap")
    if settings.OAUTH2_ENABLED:
        providers.append({"name": settings.OAUTH2_PROVIDER_NAME, "type": "oauth2"})
    return {"providers": providers}


@router.post("/ldap/login", response_model=TokenResponse)
async def ldap_login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await LdapService().authenticate(db, request.username, request.password)
    return TokenResponse(
        access_token=result["access_token"],
        token_type=result.get("token_type", "bearer"),
        user_id=result["user_id"],
        username=result["username"],
        real_name=result["real_name"],
    )


@router.get("/oauth2/authorize")
async def oauth2_authorize():
    service = OAuth2Service()
    auth_url, _ = service.get_authorize_url()
    return RedirectResponse(url=auth_url)


@router.get("/oauth2/callback")
async def oauth2_callback(
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
