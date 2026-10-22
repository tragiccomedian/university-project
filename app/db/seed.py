"""Database seed script for demo and frontend development."""

import asyncio
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.habit import Habit
from app.models.habit_checkin import HabitCheckin
from app.models.label import Label
from app.models.milestone import Milestone
from app.models.note import Note
from app.models.notification import Notification
from app.models.notification_setting import NotificationSetting
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


async def seed() -> None:
    print("🌱 Seeding database with demo data...")

    async with async_session_factory() as session:
        # Check if users already exist
        res = await session.execute(select(User).limit(1))
        if res.scalar_one_or_none() is not None:
            print("⚠️ Database already contains data. Skipping seed.")
            return

        demo_password = hash_password("Password123")

        # ── 1. Users ─────────────────────────────────────────────────────────
        alice = User(
            email="alice@example.com",
            username="alice",
            password_hash=demo_password,
            display_name="Alice Owner",
            is_active=True,
            is_verified=True,
        )
        bob = User(
            email="bob@example.com",
            username="bob",
            password_hash=demo_password,
            display_name="Bob Developer",
            is_active=True,
            is_verified=True,
        )
        charlie = User(
            email="charlie@example.com",
            username="charlie",
            password_hash=demo_password,
            display_name="Charlie Reviewer",
            is_active=True,
            is_verified=True,
        )
        session.add_all([alice, bob, charlie])
        await session.flush()

        # Notification settings
        for u in (alice, bob, charlie):
            session.add_all(
                [
                    NotificationSetting(user_id=u.id, channel="in_app", is_enabled=True),
                    NotificationSetting(user_id=u.id, channel="email", is_enabled=False),
                    NotificationSetting(user_id=u.id, channel="telegram", is_enabled=False),
                ]
            )

        # ── 2. Workspaces ─────────────────────────────────────────────────────
        ws = Workspace(
            name="TaskFlow Dev Team",
            slug="taskflow-team",
            description="Main development team workspace for TaskFlow application",
            owner_id=alice.id,
        )
        session.add(ws)
        await session.flush()

        # Members
        session.add_all(
            [
                WorkspaceMember(
                    workspace_id=ws.id,
                    user_id=alice.id,
                    role="owner",
                    status="active",
                    joined_at=datetime.now(UTC),
                ),
                WorkspaceMember(
                    workspace_id=ws.id,
                    user_id=bob.id,
                    role="member",
                    status="active",
                    joined_at=datetime.now(UTC),
                ),
                WorkspaceMember(
                    workspace_id=ws.id,
                    user_id=charlie.id,
                    role="viewer",
                    status="active",
                    joined_at=datetime.now(UTC),
                ),
            ]
        )

        # ── 3. Projects ───────────────────────────────────────────────────────
        proj_backend = Project(
            workspace_id=ws.id,
            name="Backend Core (FastAPI & PostgreSQL)",
            description="Core REST API, domain models, Redis integration and background tasks",
            status="active",
            color="#6366f1",
            start_date=date.today() - timedelta(days=7),
            end_date=date.today() + timedelta(days=30),
        )
        proj_frontend = Project(
            workspace_id=ws.id,
            name="Frontend SPA",
            description="React / Vite SPA dashboard consuming TaskFlow API",
            status="active",
            color="#06b6d4",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=45),
        )
        session.add_all([proj_backend, proj_frontend])
        await session.flush()

        # ── 4. Milestones ─────────────────────────────────────────────────────
        m1 = Milestone(
            project_id=proj_backend.id,
            title="Checkpoint 2: Architecture & Auth",
            description="Database schema, ERD, and JWT authentication completed",
            due_date=date.today() + timedelta(days=7),
            status="completed",
        )
        m2 = Milestone(
            project_id=proj_backend.id,
            title="Checkpoint 3: Real-time & Habits",
            description="WebSocket push notifications and ARQ worker integration",
            due_date=date.today() + timedelta(days=21),
            status="pending",
        )
        session.add_all([m1, m2])

        # ── 5. Labels ─────────────────────────────────────────────────────────
        lbl_bug = Label(workspace_id=ws.id, name="Bug", color="#ef4444")
        lbl_feat = Label(workspace_id=ws.id, name="Feature", color="#3b82f6")
        lbl_urgent = Label(workspace_id=ws.id, name="Urgent", color="#f59e0b")
        session.add_all([lbl_bug, lbl_feat, lbl_urgent])
        await session.flush()

        # ── 6. Tasks ──────────────────────────────────────────────────────────
        t1 = Task(
            project_id=proj_backend.id,
            workspace_id=ws.id,
            creator_id=alice.id,
            assignee_id=bob.id,
            title="Setup database migrations and Alembic",
            description="Create 18 tables, indexes, and full text search triggers",
            status="done",
            priority="high",
            start_date=date.today() - timedelta(days=3),
            due_date=date.today(),
            version=1,
        )
        t1.labels.append(lbl_feat)

        t2 = Task(
            project_id=proj_backend.id,
            workspace_id=ws.id,
            creator_id=alice.id,
            assignee_id=bob.id,
            title="Implement WebSocket notification stream",
            description="Subscribe to Redis pub/sub channels and push events to clients",
            status="in_progress",
            priority="critical",
            start_date=date.today(),
            due_date=date.today() + timedelta(days=5),
            version=1,
        )
        t2.labels.extend([lbl_feat, lbl_urgent])

        session.add_all([t1, t2])
        await session.flush()

        # ── 7. Habits & Notes ─────────────────────────────────────────────────
        habit1 = Habit(
            user_id=bob.id,
            title="Code review daily",
            frequency="daily",
            target_count=1,
            current_streak=3,
            longest_streak=5,
            streak_last_updated=date.today(),
        )
        session.add(habit1)
        await session.flush()

        session.add(
            HabitCheckin(
                habit_id=habit1.id,
                checkin_date=date.today(),
                count=1,
            )
        )

        note1 = Note(
            user_id=alice.id,
            workspace_id=ws.id,
            title="API Contract Guidelines",
            content="Always use /api/v1 prefix and standard error envelope format.",
            is_personal=False,
        )
        session.add(note1)

        # ── 8. Notification ───────────────────────────────────────────────────
        session.add(
            Notification(
                recipient_id=bob.id,
                actor_id=alice.id,
                type="MENTION",
                entity_type="task",
                entity_id=t2.id,
                payload={
                    "message": "Alice assigned you to task 'Implement WebSocket notification stream'"
                },
                is_read=False,
            )
        )

        await session.commit()
        print("✅ Demo data seeded successfully!")
        print("   Users created:")
        print("   - alice@example.com (Password123) [Owner]")
        print("   - bob@example.com   (Password123) [Member]")
        print("   - charlie@example.com (Password123) [Viewer]")


if __name__ == "__main__":
    asyncio.run(seed())
