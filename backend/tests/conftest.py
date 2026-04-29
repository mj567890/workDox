"""
Pytest fixtures for ODMS backend tests.

Strategy:
- Use PostgreSQL test database (odms_test) on the Docker db service
- Mock MinIO and other external services before app import
- Each test gets a clean database with all tables recreated
"""

import asyncio
import os
import sys
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_URL = "postgresql+asyncpg://odms:odms123@db:5432/odms_test"

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "memory://"
os.environ["REDIS_URL"] = "memory://"
os.environ["MINIO_ENDPOINT"] = "test-minio:9000"
os.environ["MINIO_ACCESS_KEY"] = "test-minio-key"
os.environ["MINIO_SECRET_KEY"] = "test-minio-secret"

# ── Mock MinIO at module level BEFORE any app imports ─────────────────────
_mock_minio_client = MagicMock()
_mock_minio_client.bucket_exists.return_value = True
_mock_minio_client.put_object.return_value = None
_mock_minio_client.get_object.return_value = MagicMock(
    data=b"mock content", content_type="text/plain"
)

# Patch the module-level singleton before it gets imported
sys.modules["app.core.storage"] = MagicMock()
sys.modules["app.core.storage"].minio_client = MagicMock()
sys.modules["app.core.storage"].minio_client.client = _mock_minio_client
sys.modules["app.core.storage"].minio_client.bucket = "test-bucket"
sys.modules["app.core.storage"].minio_client.upload_file = MagicMock(return_value="mock/path.pdf")
sys.modules["app.core.storage"].minio_client.download_file = MagicMock(return_value=b"mock")
sys.modules["app.core.storage"].minio_client.delete_file = MagicMock(return_value=None)

# Patch ws_manager to avoid Redis connection
sys.modules["app.core.ws_manager"] = MagicMock()
sys.modules["app.core.ws_manager"].ws_manager = MagicMock()
sys.modules["app.core.ws_manager"].ws_manager.initialize = MagicMock()


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session per test with clean tables."""
    import app.models.base  # noqa: F401
    import app.models.department  # noqa: F401
    import app.models.document  # noqa: F401
    import app.models.matter  # noqa: F401
    import app.models.role  # noqa: F401
    import app.models.task  # noqa: F401
    import app.models.user  # noqa: F401
    import app.models.webhook  # noqa: F401
    import app.models.workflow  # noqa: F401
    from app.models.base import Base

    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session_with_data(db_session: AsyncSession) -> AsyncSession:
    """Session pre-populated with roles and an admin + staff user."""
    from app.models.role import Role
    from app.models.user import User
    from app.core.security import hash_password

    roles = [
        Role(id=1, role_name="系统管理员", role_code="admin", description="ADMIN"),
        Role(id=2, role_name="部门领导", role_code="dept_leader", description="DEPT_LEADER"),
        Role(id=3, role_name="事项负责人", role_code="matter_owner", description="MATTER_OWNER"),
        Role(id=4, role_name="普通人员", role_code="general_staff", description="GENERAL_STAFF"),
    ]
    for role in roles:
        db_session.add(role)
    await db_session.flush()

    admin = User(
        id=1, username="admin",
        password_hash=hash_password("admin123"),
        real_name="系统管理员",
        email="admin@test.com",
        status="active",
    )
    admin.roles.append(roles[0])
    db_session.add(admin)

    staff = User(
        id=2, username="staff1",
        password_hash=hash_password("staff123"),
        real_name="普通员工",
        email="staff1@test.com",
        status="active",
    )
    staff.roles.append(roles[3])
    db_session.add(staff)
    await db_session.flush()

    return db_session


@pytest_asyncio.fixture(scope="function")
async def app(db_session: AsyncSession):
    """Create FastAPI app for API testing."""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest_asyncio.fixture(scope="function")
async def client(app, db_session) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for API testing with DB dependency overridden."""
    from app.dependencies import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
