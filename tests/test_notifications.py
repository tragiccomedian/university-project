"""Tests for Notification service and settings."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.notification_setting import NotificationSetting
from app.schemas.notification import NotificationSettingUpdate
from app.services.notification import NotificationService


@pytest.mark.asyncio
async def test_notification_creation_and_read() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    redis = AsyncMock()
    service = NotificationService(session, redis)

    recipient_id = uuid.uuid4()

    # Mock get_settings
    service.get_settings = AsyncMock(
        return_value=[NotificationSetting(user_id=recipient_id, channel="in_app", is_enabled=True)]
    )

    notif = await service.create_notification(
        recipient_id=recipient_id,
        type="MENTION",
        entity_type="task",
        entity_id=uuid.uuid4(),
        payload={"message": "You were mentioned in a task"},
    )

    assert notif.recipient_id == recipient_id
    assert notif.type == "MENTION"
    assert notif.is_read is False

    # Check that redis publish was called for real-time delivery
    assert redis.publish.called


@pytest.mark.asyncio
async def test_notification_setting_update() -> None:
    session = AsyncMock()
    redis = AsyncMock()
    service = NotificationService(session, redis)

    user_id = uuid.uuid4()
    mock_setting = NotificationSetting(user_id=user_id, channel="telegram", is_enabled=False)
    session.execute = AsyncMock(return_value=AsyncMock(scalar_one_or_none=lambda: mock_setting))

    updated = await service.update_setting(
        user_id=user_id,
        data=NotificationSettingUpdate(channel="telegram", is_enabled=True),
    )

    assert updated.channel == "telegram"
    assert updated.is_enabled is True
