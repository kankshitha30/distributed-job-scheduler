import asyncio
import os
import sys
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import Base, get_db
from app.utils.security import hash_password, create_access_token
from app.models import User, Organization, OrganizationMember

TEST_DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_scheduler.db"))
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_headers(db_session: AsyncSession) -> dict:
    user = User(
        id="test-user-id-1234",
        email="testuser@example.com",
        password_hash=hash_password("password123"),
        name="Test User",
    )
    org = Organization(
        id="test-org-id-1234",
        name="Test Org",
    )
    member = OrganizationMember(
        id="test-member-id-1234",
        organization_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db_session.add_all([user, org, member])
    await db_session.commit()

    token = create_access_token({"sub": user.id, "email": user.email, "org_id": org.id})
    return {"Authorization": f"Bearer {token}"}
