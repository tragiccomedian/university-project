"""Habit and checkin endpoints."""

import uuid

from fastapi import APIRouter, Query, status

from app.api.v1.deps import CurrentUser, HabitServiceDep
from app.schemas.habit import (
    HabitCheckinCreate,
    HabitCheckinRead,
    HabitCreate,
    HabitRead,
    HabitStats,
    HabitUpdate,
)

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=list[HabitRead], summary="List my habits")
async def list_habits(
    current_user: CurrentUser,
    service: HabitServiceDep,
) -> list[HabitRead]:
    habits = await service.list_habits(current_user)
    return [HabitRead.model_validate(h) for h in habits]


@router.post(
    "",
    response_model=HabitRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new habit",
)
async def create_habit(
    body: HabitCreate,
    current_user: CurrentUser,
    service: HabitServiceDep,
) -> HabitRead:
    habit = await service.create_habit(current_user, body)
    return HabitRead.model_validate(habit)


@router.get("/{habit_id}", response_model=HabitRead, summary="Get habit details")
async def get_habit(
    habit_id: uuid.UUID,
    current_user: CurrentUser,
    service: HabitServiceDep,
) -> HabitRead:
    habit = await service.get_habit(habit_id, current_user)
    return HabitRead.model_validate(habit)


@router.patch("/{habit_id}", response_model=HabitRead, summary="Update habit")
async def update_habit(
    habit_id: uuid.UUID,
    body: HabitUpdate,
    current_user: CurrentUser,
    service: HabitServiceDep,
) -> HabitRead:
    habit = await service.update_habit(habit_id, current_user, body)
    return HabitRead.model_validate(habit)


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete habit")
async def delete_habit(
    habit_id: uuid.UUID,
    current_user: CurrentUser,
    service: HabitServiceDep,
) -> None:
    await service.delete_habit(habit_id, current_user)


# ── Check-ins & Stats ─────────────────────────────────────────────────────────


@router.post(
    "/{habit_id}/checkins",
    response_model=HabitCheckinRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record daily/weekly checkin for habit",
    responses={
        409: {"description": "Already checked in for this date"},
    },
)
async def record_checkin(
    habit_id: uuid.UUID,
    body: HabitCheckinCreate,
    current_user: CurrentUser,
    service: HabitServiceDep,
) -> HabitCheckinRead:
    checkin = await service.record_checkin(habit_id, current_user, body)
    return HabitCheckinRead(
        id=checkin.id,
        habit_id=checkin.habit_id,
        checkin_date=checkin.checkin_date,
        count=checkin.count,
        created_at=checkin.created_at.date()
        if hasattr(checkin.created_at, "date")
        else checkin.checkin_date,
    )


@router.get(
    "/{habit_id}/checkins",
    response_model=list[HabitCheckinRead],
    summary="List checkin history for habit",
)
async def list_checkins(
    habit_id: uuid.UUID,
    current_user: CurrentUser,
    service: HabitServiceDep,
    limit: int = Query(default=60, ge=1, le=365),
) -> list[HabitCheckinRead]:
    checkins = await service.list_checkins(habit_id, current_user, limit=limit)
    return [
        HabitCheckinRead(
            id=c.id,
            habit_id=c.habit_id,
            checkin_date=c.checkin_date,
            count=c.count,
            created_at=c.created_at.date() if hasattr(c.created_at, "date") else c.checkin_date,
        )
        for c in checkins
    ]


@router.get(
    "/{habit_id}/stats",
    response_model=HabitStats,
    summary="Get habit streak and completion statistics",
)
async def get_habit_stats(
    habit_id: uuid.UUID,
    current_user: CurrentUser,
    service: HabitServiceDep,
) -> HabitStats:
    return await service.get_stats(habit_id, current_user)
