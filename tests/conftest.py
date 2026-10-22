"""Pytest test fixtures and configuration."""

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test environment variables before importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars-long-123456")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://taskflow:taskflow@localhost:5432/taskflow_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("DEBUG", "true")

from app.api.v1.deps import auth_rate_limit, rate_limit
from app.core.config import settings
from app.db.redis import get_redis
from app.db.session import get_db
from app.main import create_app


class FakeRedis:
    """In-memory async Redis stand-in for testing without an external Redis instance."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.expiries: dict[str, datetime] = {}

    def _purge_expired(self) -> None:
        now = datetime.now(UTC)
        expired_keys = [k for k, exp in self.expiries.items() if exp <= now]
        for k in expired_keys:
            self.store.pop(k, None)
            self.expiries.pop(k, None)

    async def get(self, key: str) -> str | None:
        self._purge_expired()
        return self.store.get(key)

    async def setex(self, key: str, time: int | timedelta, value: str) -> bool:
        seconds = time.total_seconds() if isinstance(time, timedelta) else time
        self.store[key] = str(value)
        self.expiries[key] = datetime.now(UTC) + timedelta(seconds=seconds)
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                self.expiries.pop(k, None)
                count += 1
        return count

    async def exists(self, *keys: str) -> int:
        self._purge_expired()
        return sum(1 for k in keys if k in self.store)

    async def incr(self, key: str, amount: int = 1) -> int:
        self._purge_expired()
        val = int(self.store.get(key, "0")) + amount
        self.store[key] = str(val)
        return val

    async def expire(self, key: str, time: int | timedelta) -> bool:
        if key not in self.store:
            return False
        seconds = time.total_seconds() if isinstance(time, timedelta) else time
        self.expiries[key] = datetime.now(UTC) + timedelta(seconds=seconds)
        return True

    async def scan(
        self, cursor: int = 0, match: str | None = None, count: int | None = None
    ) -> tuple[int, list[str]]:
        self._purge_expired()
        prefix = match.rstrip("*") if match and match.endswith("*") else match
        keys = [k for k in self.store if prefix is None or k.startswith(prefix)]
        return 0, keys

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        self.store.clear()
        self.expiries.clear()


@pytest.fixture(scope="session")
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional database session for tests.

    If PostgreSQL is unreachable, yields an AsyncMock for isolated unit testing.
    """
    test_db_url = str(settings.TEST_DATABASE_URL or settings.DATABASE_URL)
    engine = None
    try:
        engine = create_async_engine(test_db_url, pool_pre_ping=True)
        async with engine.connect():
            pass
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as s:
            yield s
            await s.rollback()
    except Exception:
        # Fallback to mock session if DB service is offline in unit test environment
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.get.return_value = None
        yield mock_session
    finally:
        if engine:
            await engine.dispose()


@pytest.fixture
async def client(
    fake_redis: FakeRedis, db_session: AsyncSession
) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client with overridden dependencies (no real rate-limits or Redis required)."""
    app = create_app()

    # Override Redis with in-memory FakeRedis
    app.dependency_overrides[get_redis] = lambda: fake_redis

    # Disable rate limits during testing
    async def noop_rate_limit() -> None:
        pass

    app.dependency_overrides[rate_limit] = noop_rate_limit
    app.dependency_overrides[auth_rate_limit] = noop_rate_limit

    # Override DB session
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
