"""
Shared pytest fixtures — in-memory SQLite DB, mocked Redis, mocked Groq,
test client, and test user factory.
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User

# ── In-memory SQLite DB ─────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables once for the test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Yield a fresh async DB session per test, rolled back afterwards."""
    async with TestSession() as session:
        yield session
        await session.rollback()


# ── Override FastAPI DB dependency ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Return an AsyncClient wired to the test database."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Patch Redis to avoid needing a live Redis server
    with patch("app.core.redis_client.is_rate_limited", return_value=False), \
         patch("app.core.redis_client.cache_get", return_value=None), \
         patch("app.core.redis_client.cache_set", new_callable=AsyncMock), \
         patch("app.core.redis_client.cache_delete", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Test user ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create and persist a test user, returning the ORM instance."""
    user = User(
        email="testuser@example.com",
        username="testuser",
        hashed_password=hash_password("SecurePass123!"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """Return Authorization headers for the test user."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "testuser@example.com", "password": "SecurePass123!"},
    )
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}
