"""Habit and HabitCheckin repositories."""

import uuid
from datetime import date

from sqlalchemy import func, select

from app.models.habit import Habit
from app.models.habit_checkin import HabitCheckin
from app.repositories.base import BaseRepository


class HabitRepository(BaseRepository[Habit]):
    model = Habit

    async def list_for_user(self, user_id: uuid.UUID) -> list[Habit]:
        query = self._base_query().where(Habit.user_id == user_id).order_by(Habit.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())


class HabitCheckinRepository(BaseRepository[HabitCheckin]):
    model = HabitCheckin

    async def get_by_date(self, habit_id: uuid.UUID, checkin_date: date) -> HabitCheckin | None:
        query = select(HabitCheckin).where(
            HabitCheckin.habit_id == habit_id,
            HabitCheckin.checkin_date == checkin_date,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_for_habit(self, habit_id: uuid.UUID, limit: int = 60) -> list[HabitCheckin]:
        query = (
            select(HabitCheckin)
            .where(HabitCheckin.habit_id == habit_id)
            .order_by(HabitCheckin.checkin_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_checkins_since(self, habit_id: uuid.UUID, since_date: date) -> int:
        query = (
            select(func.count())
            .select_from(HabitCheckin)
            .where(
                HabitCheckin.habit_id == habit_id,
                HabitCheckin.checkin_date >= since_date,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_total(self, habit_id: uuid.UUID) -> int:
        query = (
            select(func.count()).select_from(HabitCheckin).where(HabitCheckin.habit_id == habit_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one()
