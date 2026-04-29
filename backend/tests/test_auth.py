"""Tests for authentication API endpoints and service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestAuthService:
    """Test AuthService directly."""

    async def test_authenticate_success(self, db_session_with_data: AsyncSession):
        from app.services.auth_service import AuthService

        svc = AuthService()
        result = await svc.authenticate(
            db=db_session_with_data,
            username="admin",
            password="admin123",
        )

        assert result["access_token"] is not None
        assert result["token_type"] == "bearer"
        assert result["user"]["username"] == "admin"
        assert result["user"]["real_name"] == "系统管理员"
        assert len(result["user"]["roles"]) == 1
        assert result["user"]["roles"][0]["role_code"] == "admin"

    async def test_authenticate_wrong_password(self, db_session_with_data: AsyncSession):
        from app.services.auth_service import AuthService
        from app.core.exceptions import UnauthorizedException

        svc = AuthService()
        with pytest.raises(UnauthorizedException) as exc:
            await svc.authenticate(
                db=db_session_with_data,
                username="admin",
                password="wrong-password",
            )
        assert "Invalid username or password" in str(exc.value.detail)

    async def test_authenticate_nonexistent_user(self, db_session_with_data: AsyncSession):
        from app.services.auth_service import AuthService
        from app.core.exceptions import UnauthorizedException

        svc = AuthService()
        with pytest.raises(UnauthorizedException):
            await svc.authenticate(
                db=db_session_with_data,
                username="ghost",
                password="anything",
            )

    async def test_get_current_user_info(self, db_session_with_data: AsyncSession):
        from app.services.auth_service import AuthService

        svc = AuthService()
        result = await svc.get_current_user_info(
            db=db_session_with_data, user_id=1
        )

        assert result["username"] == "admin"
        assert result["status"] == "active"
        assert len(result["roles"]) == 1

    async def test_get_current_user_not_found(self, db_session_with_data: AsyncSession):
        from app.services.auth_service import AuthService
        from app.core.exceptions import NotFoundException

        svc = AuthService()
        with pytest.raises(NotFoundException):
            await svc.get_current_user_info(db=db_session_with_data, user_id=999)


class TestAuthAPI:
    """Test auth endpoints via FastAPI test client."""

    async def test_login_success(
        self, client, db_session_with_data
    ):
        from app.dependencies import get_db

        async def override():
            yield db_session_with_data
        client._transport.app.dependency_overrides[get_db] = override

        response = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "admin"

    async def test_login_wrong_password(
        self, client, db_session_with_data
    ):
        from app.dependencies import get_db

        async def override():
            yield db_session_with_data
        client._transport.app.dependency_overrides[get_db] = override

        response = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrong",
        })

        assert response.status_code == 401

    async def test_login_missing_fields(self, client):
        response = await client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422  # Pydantic validation error

    async def test_get_me_with_valid_token(
        self, client, db_session_with_data
    ):
        from app.dependencies import get_db

        async def override():
            yield db_session_with_data
        client._transport.app.dependency_overrides[get_db] = override

        from app.core.security import create_access_token
        token = create_access_token({
            "sub": "1",
            "username": "admin",
            "roles": ["admin"],
        })

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"

    async def test_get_me_without_token(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_me_with_invalid_token(
        self, client, db_session_with_data
    ):
        from app.dependencies import get_db

        async def override():
            yield db_session_with_data
        client._transport.app.dependency_overrides[get_db] = override

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.here"},
        )
        assert response.status_code == 401
