"""Notification REST endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import CurrentUser, DbDep, RedisDep
from app.schemas.auth import UserPublic
from app.schemas.notification import (
    NotificationRead,
    NotificationSettingRead,
    NotificationSettingUpdate,
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(session: DbDep, redis: RedisDep) -> NotificationService:
    return NotificationService(session, redis)


NotificationServiceDep = Depends(get_notification_service)


@router.get("", response_model=list[NotificationRead], summary="List my notifications")
async def list_notifications(
    current_user: CurrentUser,
    service: NotificationService = NotificationServiceDep,
    is_read: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[NotificationRead]:
    notifications = await service.list_notifications(
        recipient_id=current_user.id,
        is_read=is_read,
        limit=limit,
        offset=offset,
    )
    return [
        NotificationRead(
            id=n.id,
            recipient_id=n.recipient_id,
            actor_id=n.actor_id,
            type=n.type,  # type: ignore[arg-type]
            entity_type=n.entity_type,
            entity_id=n.entity_id,
            payload=n.payload,
            is_read=n.is_read,
            read_at=n.read_at,
            created_at=n.created_at,
            actor=UserPublic.model_validate(n.actor) if n.actor else None,
        )
        for n in notifications
    ]


@router.patch("/{n_id}/read", response_model=NotificationRead, summary="Mark notification as read")
async def mark_as_read(
    n_id: uuid.UUID,
    current_user: CurrentUser,
    service: NotificationService = NotificationServiceDep,
) -> NotificationRead:
    notification = await service.mark_as_read(n_id, current_user.id)
    return NotificationRead(
        id=notification.id,
        recipient_id=notification.recipient_id,
        actor_id=notification.actor_id,
        type=notification.type,  # type: ignore[arg-type]
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
        payload=notification.payload,
        is_read=notification.is_read,
        read_at=notification.read_at,
        created_at=notification.created_at,
        actor=UserPublic.model_validate(notification.actor) if notification.actor else None,
    )


@router.post("/read-all", summary="Mark all notifications as read")
async def mark_all_as_read(
    current_user: CurrentUser,
    service: NotificationService = NotificationServiceDep,
) -> dict:
    count = await service.mark_all_as_read(current_user.id)
    return {"status": "ok", "marked_read_count": count}


@router.get(
    "/settings",
    response_model=list[NotificationSettingRead],
    summary="Get notification channel settings",
)
async def get_notification_settings(
    current_user: CurrentUser,
    service: NotificationService = NotificationServiceDep,
) -> list[NotificationSettingRead]:
    settings = await service.get_settings(current_user.id)
    return [NotificationSettingRead.model_validate(s) for s in settings]


@router.put(
    "/settings",
    response_model=NotificationSettingRead,
    summary="Update notification channel setting",
)
async def update_notification_setting(
    body: NotificationSettingUpdate,
    current_user: CurrentUser,
    service: NotificationService = NotificationServiceDep,
) -> NotificationSettingRead:
    setting = await service.update_setting(current_user.id, body)
    return NotificationSettingRead.model_validate(setting)
