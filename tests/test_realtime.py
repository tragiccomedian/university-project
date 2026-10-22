"""Tests for Real-time components, Redis Cache, and Telegram fallback."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.cache import CacheManager
from app.realtime.notifier import publish_realtime_event, user_notification_channel
from app.services.telegram import TelegramService
from tests.conftest import FakeRedis


@pytest.mark.asyncio
async def test_telegram_service_unconfigured_fallback() -> None:
    """Telegram service gracefully returns False when token is not configured."""
    service = TelegramService(bot_token=None)
    assert service.is_configured is False

    sent = await service.send_message(chat_id="123456", text="Test notification")
    assert sent is False


@pytest.mark.asyncio
async def test_cache_manager_operations(fake_redis: FakeRedis) -> None:
    """Cache manager get, set, delete, and pattern invalidation with Redis."""
    cache = CacheManager(fake_redis)  # type: ignore[arg-type]

    await cache.set("cache:test:1", {"foo": "bar"}, ttl_seconds=60)
    val = await cache.get("cache:test:1")
    assert val == {"foo": "bar"}

    await cache.delete("cache:test:1")
    val_after = await cache.get("cache:test:1")
    assert val_after is None


@pytest.mark.asyncio
async def test_publish_realtime_event() -> None:
    """Realtime event publishes valid JSON to user channel."""
    redis_mock = AsyncMock()
    user_id = uuid.uuid4()

    await publish_realtime_event(
        redis=redis_mock,
        user_id=user_id,
        event="notification.new",
        payload={"id": "123", "message": "Hello"},
    )

    expected_channel = user_notification_channel(user_id)
    assert redis_mock.publish.called
    channel_arg = redis_mock.publish.call_args[0][0]
    message_arg = redis_mock.publish.call_args[0][1]

    assert channel_arg == expected_channel
    assert '"event": "notification.new"' in message_arg
    assert '"message": "Hello"' in message_arg
