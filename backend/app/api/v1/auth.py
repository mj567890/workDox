from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.auth_service import AuthService

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
