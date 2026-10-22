"""Real-time notification broadcaster and Redis Pub/Sub bridge."""

import asyncio
import json
import uuid
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)

CHANNEL_PREFIX = "notifications:"


def user_notification_channel(user_id: uuid.UUID) -> str:
    return f"{CHANNEL_PREFIX}{user_id}"


async def publish_realtime_event(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Publish a structured event to user's Redis Pub/Sub channel."""
    message = json.dumps({"event": event, "payload": payload}, default=str)
    channel = user_notification_channel(user_id)
    await redis.publish(channel, message)
    logger.debug("Published realtime event", channel=channel, event_name=event)


class NotificationConnectionManager:
    """Manages active WebSockets and bridges Redis Pub/Sub events to connected clients."""

    def __init__(self) -> None:
        # Maps user_id -> set of active WebSockets
        self.active_connections: dict[uuid.UUID, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID) -> None:
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(
            "WebSocket connected",
            user_id=str(user_id),
            connections_count=len(self.active_connections[user_id]),
        )

    def disconnect(self, websocket: WebSocket, user_id: uuid.UUID) -> None:
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info("WebSocket disconnected", user_id=str(user_id))

    async def listen_and_forward(
        self,
        websocket: WebSocket,
        user_id: uuid.UUID,
        redis: aioredis.Redis,
    ) -> None:
        """Listen to user's Redis Pub/Sub channel and forward messages to the WebSocket."""
        pubsub = redis.pubsub()
        channel = user_notification_channel(user_id)
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    raw_data = message["data"]
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    data = json.loads(raw_data)
                    await websocket.send_json(data)
        except (asyncio.CancelledError, Exception) as exc:
            logger.debug("Pub/sub listener ended", user_id=str(user_id), error=str(exc))
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


ws_manager = NotificationConnectionManager()
