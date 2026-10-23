"""Import all models so Alembic autogenerate discovers them."""

from app.models.activity_log import ActivityLog
from app.models.attachment import Attachment
from app.models.comment import Comment
from app.models.habit import Habit
from app.models.habit_checkin import HabitCheckin
from app.models.label import Label
from app.models.milestone import Milestone
from app.models.note import Note
from app.models.notification import Notification
from app.models.notification_setting import NotificationSetting
from app.models.project import Project
from app.models.refresh_token import RefreshToken
from app.models.task import Task
from app.models.task_label import task_labels
from app.models.time_entry import TimeEntry
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember

__all__ = [
    "User",
    "RefreshToken",
    "Workspace",
    "WorkspaceMember",
    "Project",
    "Task",
    "Label",
    "task_labels",
    "Comment",
    "Milestone",
    "TimeEntry",
    "Habit",
    "HabitCheckin",
    "Note",
    "Attachment",
    "Notification",
    "NotificationSetting",
    "ActivityLog",
]
