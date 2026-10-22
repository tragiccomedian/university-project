"""Habit service with checkin tracking and streak statistics."""

import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.habit import Habit
from app.models.habit_checkin import HabitCheckin
from app.models.user import User
from app.repositories.habit import HabitCheckinRepository, HabitRepository
from app.schemas.habit import HabitCheckinCreate, HabitCreate, HabitStats, HabitUpdate


class HabitService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.habit_repo = HabitRepository(session)
        self.checkin_repo = HabitCheckinRepository(session)

    async def create_habit(self, user: User, data: HabitCreate) -> Habit:
        return await self.habit_repo.create(
            user_id=user.id,
            title=data.title,
            description=data.description,
            frequency=data.frequency,
            target_count=data.target_count,
            current_streak=0,
            longest_streak=0,
        )

    async def get_habit(self, habit_id: uuid.UUID, user: User) -> Habit:
        habit = await self.habit_repo.get(habit_id)
        if not habit or habit.user_id != user.id:
            raise NotFoundError("Habit not found.")
        return habit

    async def update_habit(self, habit_id: uuid.UUID, user: User, data: HabitUpdate) -> Habit:
        habit = await self.get_habit(habit_id, user)
        updates = data.model_dump(exclude_unset=True)
        return await self.habit_repo.update(habit, **updates)

    async def delete_habit(self, habit_id: uuid.UUID, user: User) -> None:
        habit = await self.get_habit(habit_id, user)
        await self.habit_repo.soft_delete(habit)

    async def list_habits(self, user: User) -> list[Habit]:
        return await self.habit_repo.list_for_user(user.id)

    # ── Check-ins ─────────────────────────────────────────────────────────────

    async def record_checkin(
        self, habit_id: uuid.UUID, user: User, data: HabitCheckinCreate
    ) -> HabitCheckin:
        habit = await self.get_habit(habit_id, user)
        checkin_date = data.checkin_date or date.today()

        # Check for duplicate checkin on the same date
        existing = await self.checkin_repo.get_by_date(habit_id, checkin_date)
        if existing:
            raise ConflictError(f"Habit has already been checked in for {checkin_date}.")

        return await self.checkin_repo.create(
            habit_id=habit.id,
            checkin_date=checkin_date,
            count=data.count,
        )

    async def list_checkins(
        self, habit_id: uuid.UUID, user: User, limit: int = 60
    ) -> list[HabitCheckin]:
        habit = await self.get_habit(habit_id, user)
        return await self.checkin_repo.list_for_habit(habit.id, limit=limit)

    async def get_stats(self, habit_id: uuid.UUID, user: User) -> HabitStats:
        habit = await self.get_habit(habit_id, user)
        since_30d = date.today() - timedelta(days=30)
        recent_count = await self.checkin_repo.count_checkins_since(habit.id, since_30d)
        total_count = await self.checkin_repo.count_total(habit.id)

        completion_rate = round(min(100.0, (recent_count / 30.0) * 100.0), 1)

        return HabitStats(
            habit_id=habit.id,
            title=habit.title,
            current_streak=habit.current_streak,
            longest_streak=habit.longest_streak,
            total_checkins=total_count,
            completion_rate_30d=completion_rate,
        )
