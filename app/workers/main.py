"""ARQ background worker settings and task definitions.

Tasks registered here:
  - recalculate_streaks: daily at 00:05 — updates habit streaks
  - send_deadline_reminders: hourly — notifies on tasks due tomorrow
  - cleanup_expired_tokens: every 6h — removes expired RefreshToken rows
  - cleanup_soft_deleted: weekly — hard-deletes records soft-deleted >30 days ago

ARQ uses Redis as both a queue and a result store.
Workers are started separately via: python -m arq app.workers.main.WorkerSettings
"""

from datetime import UTC, datetime, timedelta

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Task functions ────────────────────────────────────────────────────────────


async def recalculate_streaks(ctx: dict) -> None:
    """Recalculate current_streak and longest_streak for all active habits."""
    from sqlalchemy import select, update

    from app.db.session import async_session_factory
    from app.models.habit import Habit
    from app.models.habit_checkin import HabitCheckin

    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)

    async with async_session_factory() as session:
        habits_result = await session.execute(select(Habit).where(Habit.deleted_at.is_(None)))
        habits = list(habits_result.scalars().all())

        for habit in habits:
            # Get the last checkin date
            last_checkin_result = await session.execute(
                select(HabitCheckin.checkin_date)
                .where(HabitCheckin.habit_id == habit.id)
                .order_by(HabitCheckin.checkin_date.desc())
                .limit(1)
            )
            last_date = last_checkin_result.scalar_one_or_none()

            if last_date is None or last_date < yesterday:
                # Streak broken — reset to 0
                new_streak = 0
            else:
                new_streak = habit.current_streak + (1 if last_date == today else 0)

            new_longest = max(habit.longest_streak, new_streak)
            await session.execute(
                update(Habit)
                .where(Habit.id == habit.id)
                .values(
                    current_streak=new_streak,
                    longest_streak=new_longest,
                    streak_last_updated=today,
                )
            )
        await session.commit()

    logger.info("recalculate_streaks completed", habits_processed=len(habits))


async def send_deadline_reminders(ctx: dict) -> None:
    """Create DEADLINE notifications for tasks due tomorrow."""
    from sqlalchemy import select

    from app.db.session import async_session_factory
    from app.models.notification import Notification
    from app.models.task import Task

    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()

    async with async_session_factory() as session:
        tasks_result = await session.execute(
            select(Task).where(
                Task.due_date == tomorrow,
                Task.deleted_at.is_(None),
                Task.status.not_in(["done", "cancelled"]),
                Task.assignee_id.is_not(None),
            )
        )
        tasks = list(tasks_result.scalars().all())

        for task in tasks:
            session.add(
                Notification(
                    recipient_id=task.assignee_id,
                    actor_id=None,
                    type="DEADLINE",
                    entity_type="task",
                    entity_id=task.id,
                    payload={"task_title": task.title, "due_date": str(task.due_date)},
                )
            )
        await session.commit()

    logger.info("send_deadline_reminders completed", tasks=len(tasks))


async def cleanup_expired_tokens(ctx: dict) -> None:
    """Remove expired RefreshToken rows from the database."""
    from app.db.session import async_session_factory
    from app.repositories.token import RefreshTokenRepository

    async with async_session_factory() as session:
        repo = RefreshTokenRepository(session)
        deleted = await repo.delete_expired()
        await session.commit()

    logger.info("cleanup_expired_tokens completed", deleted=deleted)


async def cleanup_soft_deleted(ctx: dict) -> None:
    """Hard-delete records soft-deleted more than 30 days ago."""
    from sqlalchemy import delete as sql_delete

    from app.db.session import async_session_factory
    from app.models.comment import Comment
    from app.models.note import Note
    from app.models.task import Task

    cutoff = datetime.now(UTC) - timedelta(days=30)

    async with async_session_factory() as session:
        for model in (Comment, Note, Task):
            await session.execute(
                sql_delete(model).where(
                    model.deleted_at.is_not(None),  # type: ignore[attr-defined]
                    model.deleted_at < cutoff,  # type: ignore[attr-defined]
                )
            )
        await session.commit()

    logger.info("cleanup_soft_deleted completed", cutoff=str(cutoff))


# ── Worker settings ───────────────────────────────────────────────────────────


class WorkerSettings:
    """ARQ worker configuration."""

    redis_settings = RedisSettings.from_dsn(settings.redis_url_str)

    functions = [
        recalculate_streaks,
        send_deadline_reminders,
        cleanup_expired_tokens,
        cleanup_soft_deleted,
    ]

    cron_jobs = [
        cron(recalculate_streaks, hour=0, minute=5),  # daily 00:05
        cron(send_deadline_reminders, minute=0),  # every hour
        cron(cleanup_expired_tokens, hour={0, 6, 12, 18}, minute=0),  # 4× daily
        cron(cleanup_soft_deleted, weekday=0, hour=3, minute=0),  # weekly Monday 03:00
    ]

    max_jobs = 10
    job_timeout = 300  # 5 minutes max per job
    retry_jobs = True
    max_tries = 3
