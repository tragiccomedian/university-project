"""WebSocket endpoint for real-time notification streaming."""

import asyncio
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.db.redis import redis_client
from app.db.session import async_session_factory
from app.realtime.notifier import ws_manager
from app.services.auth import AuthService
from app.services.notification import NotificationService

logger = get_logger(__name__)

router = APIRouter(tags=["real-time notifications"])


@router.websocket("/ws/notifications")
async def notifications_websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """Real-time notifications WebSocket. Authenticates via ?token=<access_token>."""
    if not token:
        await websocket.close(code=4401, reason="Authentication token missing")
        return

    # Verify access token
    async with async_session_factory() as session:
        auth_service = AuthService(session, redis_client)
        try:
            payload = await auth_service.verify_access_token(token)
            user_id = uuid.UUID(payload["sub"])
        except Exception as exc:
            logger.warning("WebSocket authentication rejected", error=str(exc))
            await websocket.close(code=4401, reason="Invalid or expired token")
            return

    await ws_manager.connect(websocket, user_id)

    # Spawn background task to listen to Redis Pub/Sub and forward to WebSocket
    forward_task = asyncio.create_task(
        ws_manager.listen_and_forward(websocket, user_id, redis_client)
    )

    try:
        while True:
            # Receive client-side events
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "ping":
                await websocket.send_json({"event": "pong"})

            elif event == "mark_read":
                notif_id_str = data.get("payload", {}).get("notification_id")
                if notif_id_str:
                    try:
                        notif_id = uuid.UUID(notif_id_str)
                        async with async_session_factory() as session:
                            notif_service = NotificationService(session, redis_client)
                            await notif_service.mark_as_read(notif_id, user_id)
                            await session.commit()
                        await websocket.send_json(
                            {
                                "event": "notification.read",
                                "payload": {"notification_id": str(notif_id)},
                            }
                        )
                    except Exception as exc:
                        logger.warning("Error handling mark_read via WS", error=str(exc))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client", user_id=str(user_id))
    except Exception as exc:
        logger.warning("WebSocket loop encountered an error", error=str(exc))
    finally:
        forward_task.cancel()
        ws_manager.disconnect(websocket, user_id)
