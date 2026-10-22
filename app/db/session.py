"""Async SQLAlchemy engine and session factory.

Design:
- Single engine per process (connection pool).
- async_sessionmaker wraps each request in a session via FastAPI dependency.
- expire_on_commit=False avoids lazy-load errors after commit in async context.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.database_url_str,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # detect stale connections
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a DB session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
