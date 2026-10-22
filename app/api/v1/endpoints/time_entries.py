"""Time tracking endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Query, status

from app.api.v1.deps import (
    CurrentUser,
    RequireMember,
    TimeTrackingServiceDep,
)
from app.schemas.time_entry import (
    TimeEntryManualCreate,
    TimeEntryRead,
    TimeEntryStart,
)

router = APIRouter(tags=["time tracking"])


# ── Task-scoped timer start ───────────────────────────────────────────────────


@router.post(
    "/workspaces/{ws_id}/tasks/{task_id}/time-entries/start",
    response_model=TimeEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start timer for a task",
    responses={
        409: {"description": "Active timer is already running for this user"},
    },
)
async def start_timer(
    task_id: uuid.UUID,
    body: TimeEntryStart,
    ctx: RequireMember,
    service: TimeTrackingServiceDep,
) -> TimeEntryRead:
    entry = await service.start_timer(ctx.workspace.id, task_id, ctx.user, body)
    return TimeEntryRead.model_validate(entry)


# ── Global time entries ───────────────────────────────────────────────────────


@router.post(
    "/time-entries/stop",
    response_model=TimeEntryRead,
    summary="Stop current active timer",
    responses={
        404: {"description": "No active timer found"},
    },
)
async def stop_timer(
    current_user: CurrentUser,
    service: TimeTrackingServiceDep,
) -> TimeEntryRead:
    entry = await service.stop_timer(current_user)
    return TimeEntryRead.model_validate(entry)


@router.get(
    "/time-entries/active",
    response_model=TimeEntryRead | None,
    summary="Get active running timer if any",
)
async def get_active_timer(
    current_user: CurrentUser,
    service: TimeTrackingServiceDep,
) -> TimeEntryRead | None:
    entry = await service.get_active_timer(current_user)
    return TimeEntryRead.model_validate(entry) if entry else None


@router.post(
    "/time-entries",
    response_model=TimeEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log time manually",
)
async def create_manual_entry(
    body: TimeEntryManualCreate,
    current_user: CurrentUser,
    service: TimeTrackingServiceDep,
) -> TimeEntryRead:
    entry = await service.create_manual_entry(current_user, body)
    return TimeEntryRead.model_validate(entry)


@router.get(
    "/time-entries",
    response_model=list[TimeEntryRead],
    summary="List logged time entries for current user",
)
async def list_time_entries(
    current_user: CurrentUser,
    service: TimeTrackingServiceDep,
    task_id: uuid.UUID | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[TimeEntryRead]:
    entries = await service.list_user_entries(
        user_id=current_user.id,
        task_id=task_id,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=offset,
    )
    return [TimeEntryRead.model_validate(e) for e in entries]
