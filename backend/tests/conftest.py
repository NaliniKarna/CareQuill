import os
import uuid

# Force test settings before any app module is imported so `settings` picks
# up the test database and a predictable JWT secret.
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://medqueue:medqueue_dev_pw@localhost:5432/medqueue_ai_test",
    ),
)
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production-use"
os.environ["EMAIL_BACKEND"] = "console"
os.environ["AI_ENABLED"] = "false"
os.environ["OCR_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.dependencies.db import get_db
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine as app_engine
from app.main import app

settings = get_settings()

test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)




@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    """Truncate every table between tests so each test starts from a blank
    slate without paying the cost of recreating the schema each time."""
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    # `app.db.session.engine` (a pooled engine, unlike the NullPool
    # `test_engine` above) is only exercised by code that opens its own
    # session outside the request lifecycle -- namely the background
    # document-processing task via `session_scope()`. Pytest-asyncio gives
    # each test function its own event loop, so a connection left in that
    # pool from one test would be bound to a now-closed loop by the next
    # test. Disposing here forces a fresh connection (and loop binding) per
    # test, the same way `test_engine`'s NullPool avoids the problem for
    # the request-lifecycle session.
    await app_engine.dispose()


async def _override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def client():
    # `raise_app_exceptions=False`: by default Starlette's
    # ServerErrorMiddleware re-raises the original exception after sending
    # its response, specifically so a test client CAN surface it -- but a
    # real deployment (uvicorn) never does that to the caller, it only
    # returns the generic 500 JSON response. Matching that production
    # behavior here lets a test assert on the actual HTTP response for an
    # unhandled-exception path (see test_security_audit.py) instead of the
    # request itself raising.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def unique_email():
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


async def register_and_login(
    client: AsyncClient, email: str, password: str = "SuperSecret#123"
) -> dict:
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password, "accepted_terms": True}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
