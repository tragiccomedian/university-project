"""Notification service for delivery, settings, and real-time dispatch."""

import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models.notification import Notification
from app.models.notification_setting import NotificationSetting
from app.realtime.notifier import publish_realtime_event
from app.schemas.notification import NotificationSettingUpdate
from app.services.telegram import TelegramService


class NotificationService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis) -> None:
        self.session = session
        self.redis = redis
        self.telegram = TelegramService()

    async def create_notification(
        self,
        recipient_id: uuid.UUID,
        type: str,
        entity_type: str,
        entity_id: uuid.UUID,
        payload: dict[str, Any],
        actor_id: uuid.UUID | None = None,
    ) -> Notification:
        """Create notification, persist in DB, and dispatch to active channels (WebSocket / Telegram)."""
        notification = Notification(
            recipient_id=recipient_id,
            actor_id=actor_id,
            type=type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            is_read=False,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)

        # Check channel settings
        settings = await self.get_settings(recipient_id)
        settings_map = {s.channel: s.is_enabled for s in settings}

        # 1. In-app Real-time push via Redis Pub/Sub
        if settings_map.get("in_app", True):
            event_payload = {
                "id": str(notification.id),
                "type": notification.type,
                "entity_type": notification.entity_type,
                "entity_id": str(notification.entity_id),
                "message": payload.get("message", f"New notification: {type}"),
                "created_at": notification.created_at.isoformat()
                if notification.created_at
                else datetime.now(UTC).isoformat(),
            }
            await publish_realtime_event(
                self.redis,
                recipient_id,
                "notification.new",
                event_payload,
            )

        # 2. Telegram Bot notification (if enabled and telegram_chat_id in payload or user profile)
        if settings_map.get("telegram", False) and self.telegram.is_configured:
            chat_id = payload.get("telegram_chat_id")
            if chat_id:
                msg = f"🔔 *TaskFlow Notification*\n\n{payload.get('message', type)}"
                await self.telegram.send_message(chat_id, msg)

        return notification

    async def list_notifications(
        self,
        recipient_id: uuid.UUID,
        is_read: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        query = (
            select(Notification)
            .where(Notification.recipient_id == recipient_id)
            .options(selectinload(Notification.actor))
        )
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)

        query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(
        self, notification_id: uuid.UUID, recipient_id: uuid.UUID
    ) -> Notification:
        query = select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == recipient_id,
        )
        res = await self.session.execute(query)
        notification = res.scalar_one_or_none()
        if not notification:
            raise NotFoundError("Notification not found.")

        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        await self.session.flush()

        # Broadcast read confirmation to sync open client tabs
        await publish_realtime_event(
            self.redis,
            recipient_id,
            "notification.read",
            {"notification_id": str(notification.id)},
        )
        return notification

    async def mark_all_as_read(self, recipient_id: uuid.UUID) -> int:
        stmt = (
            update(Notification)
            .where(Notification.recipient_id == recipient_id, Notification.is_read == False)  # noqa: E712
            .values(is_read=True, read_at=datetime.now(UTC))
        )
        res = await self.session.execute(stmt)
        return res.rowcount  # type: ignore[return-value]

    # ── Channel Settings ──────────────────────────────────────────────────────

    async def get_settings(self, user_id: uuid.UUID) -> list[NotificationSetting]:
        query = select(NotificationSetting).where(NotificationSetting.user_id == user_id)
        result = await self.session.execute(query)
        settings = list(result.scalars().all())

        # If user has no settings populated yet, create defaults
        if not settings:
            for channel in ("in_app", "email", "telegram"):
                ns = NotificationSetting(
                    user_id=user_id,
                    channel=channel,
                    is_enabled=(channel == "in_app"),
                )
                self.session.add(ns)
                settings.append(ns)
            await self.session.flush()

        return settings

    async def update_setting(
        self, user_id: uuid.UUID, data: NotificationSettingUpdate
    ) -> NotificationSetting:
        query = select(NotificationSetting).where(
            NotificationSetting.user_id == user_id,
            NotificationSetting.channel == data.channel,
        )
        res = await self.session.execute(query)
        setting = res.scalar_one_or_none()
        if not setting:
            setting = NotificationSetting(
                user_id=user_id,
                channel=data.channel,
                is_enabled=data.is_enabled,
            )
            self.session.add(setting)
        else:
            setting.is_enabled = data.is_enabled

        await self.session.flush()
        return setting
