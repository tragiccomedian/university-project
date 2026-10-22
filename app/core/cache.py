"""Redis caching helper with invalidation patterns."""

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Provides typed get/set/delete with JSON serialization and key pattern invalidation."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis

    async def get(self, key: str) -> Any | None:
        try:
            val = await self.redis.get(key)
            if val is not None:
                return json.loads(val)
        except Exception as exc:
            logger.warning("Cache get failed", key=key, error=str(exc))
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        try:
            serialized = json.dumps(value, default=str)
            await self.redis.setex(key, ttl_seconds, serialized)
        except Exception as exc:
            logger.warning("Cache set failed", key=key, error=str(exc))

    async def delete(self, key: str) -> None:
        try:
            await self.redis.delete(key)
        except Exception as exc:
            logger.warning("Cache delete failed", key=key, error=str(exc))

    async def invalidate_pattern(self, pattern: str) -> None:
        """Scan and remove keys matching a pattern (e.g. 'cache:tasks:123:*')."""
        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning("Cache pattern invalidation failed", pattern=pattern, error=str(exc))
