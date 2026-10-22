"""Async Redis client singleton."""

import redis.asyncio as aioredis

from app.core.config import settings

# Single connection pool shared across the app
redis_client: aioredis.Redis = aioredis.from_url(
    settings.redis_url_str,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency that returns the shared Redis client."""
    return redis_client
