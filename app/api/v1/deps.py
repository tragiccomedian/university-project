"""FastAPI dependency functions (DI wiring) and RBAC security."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Path, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from app.db.redis import get_redis
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceMemberRepository, WorkspaceRepository
from app.services.attachment import AttachmentService
from app.services.auth import AuthService
from app.services.comment import CommentService
from app.services.habit import HabitService
from app.services.milestone import MilestoneService
from app.services.note import NoteService
from app.services.project import ProjectService
from app.services.search import SearchService
from app.services.task import TaskService
from app.services.time_tracking import TimeTrackingService
from app.services.workspace import WorkspaceService

_bearer = HTTPBearer(auto_error=False)


# ── Database & Redis ──────────────────────────────────────────────────────────

DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]


# ── Services ──────────────────────────────────────────────────────────────────


def get_auth_service(session: DbDep, redis: RedisDep) -> AuthService:
    return AuthService(session, redis)


def get_workspace_service(session: DbDep) -> WorkspaceService:
    return WorkspaceService(session)


def get_project_service(session: DbDep) -> ProjectService:
    return ProjectService(session)


def get_task_service(session: DbDep) -> TaskService:
    return TaskService(session)


def get_comment_service(session: DbDep) -> CommentService:
    return CommentService(session)


def get_milestone_service(session: DbDep) -> MilestoneService:
    return MilestoneService(session)


def get_time_tracking_service(session: DbDep) -> TimeTrackingService:
    return TimeTrackingService(session)


def get_habit_service(session: DbDep) -> HabitService:
    return HabitService(session)


def get_note_service(session: DbDep) -> NoteService:
    return NoteService(session)


def get_attachment_service(session: DbDep) -> AttachmentService:
    return AttachmentService(session)


def get_search_service(session: DbDep) -> SearchService:
    return SearchService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
MilestoneServiceDep = Annotated[MilestoneService, Depends(get_milestone_service)]
TimeTrackingServiceDep = Annotated[TimeTrackingService, Depends(get_time_tracking_service)]
HabitServiceDep = Annotated[HabitService, Depends(get_habit_service)]
NoteServiceDep = Annotated[NoteService, Depends(get_note_service)]
AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]


# ── Current User ──────────────────────────────────────────────────────────────


async def get_current_user(
    session: DbDep,
    auth_service: AuthServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    """Validate Bearer token and return the authenticated User."""
    if not credentials:
        raise AuthenticationError("Authorization header is missing.")

    payload = await auth_service.verify_access_token(credentials.credentials)

    user_id = uuid.UUID(payload["sub"])
    user = await UserRepository(session).get(user_id)
    if not user or not user.is_active:
        raise AuthenticationError("User account not found or inactive.")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Token metadata for logout ─────────────────────────────────────────────────


class TokenMeta:
    """Carries jti + expires_at extracted from the current access token."""

    def __init__(self, jti: str, expires_at: datetime) -> None:
        self.jti = jti
        self.expires_at = expires_at


async def get_token_meta(
    auth_service: AuthServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> TokenMeta:
    if not credentials:
        raise AuthenticationError("Authorization header is missing.")
    payload = await auth_service.verify_access_token(credentials.credentials)
    return TokenMeta(
        jti=payload["jti"],
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )


TokenMetaDep = Annotated[TokenMeta, Depends(get_token_meta)]


# ── RBAC & Workspace Context ──────────────────────────────────────────────────

ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 1,
    "member": 2,
    "admin": 3,
    "owner": 4,
}


class WorkspaceContext:
    """Context container for an authorized user operating inside a workspace."""

    def __init__(
        self,
        workspace: Workspace,
        membership: WorkspaceMember,
        user: User,
    ) -> None:
        self.workspace = workspace
        self.membership = membership
        self.user = user

    @property
    def role(self) -> str:
        return self.membership.role


def require_role(min_role: str = "viewer") -> Callable:
    """Dependency factory checking that current user is an active member with >= min_role."""

    async def _dependency(
        ws_id: Annotated[uuid.UUID, Path(...)],
        current_user: CurrentUser,
        session: DbDep,
    ) -> WorkspaceContext:
        ws_repo = WorkspaceRepository(session)
        member_repo = WorkspaceMemberRepository(session)

        workspace = await ws_repo.get(ws_id)
        if not workspace:
            raise NotFoundError("Workspace not found.")

        membership = await member_repo.get_membership(ws_id, current_user.id)
        # Security design decision: return 404 if user is not a member (do not leak existence)
        if not membership or membership.status != "active":
            raise NotFoundError("Workspace not found.")

        # Check role hierarchy: return 403 if role is insufficient
        user_level = ROLE_HIERARCHY.get(membership.role, 0)
        required_level = ROLE_HIERARCHY.get(min_role, 0)
        if user_level < required_level:
            raise PermissionDeniedError(
                f"Action requires '{min_role}' role or higher in this workspace."
            )

        return WorkspaceContext(workspace, membership, current_user)

    return _dependency


RequireViewer = Annotated[WorkspaceContext, Depends(require_role("viewer"))]
RequireMember = Annotated[WorkspaceContext, Depends(require_role("member"))]
RequireAdmin = Annotated[WorkspaceContext, Depends(require_role("admin"))]
RequireOwner = Annotated[WorkspaceContext, Depends(require_role("owner"))]


# ── Rate limiting ─────────────────────────────────────────────────────────────


async def rate_limit(
    request: Request,
    redis: RedisDep,
) -> None:
    """Global IP-based rate limiter using Redis INCR+EXPIRE (sliding window)."""
    from app.core.config import settings

    ip = request.client.host if request.client else "unknown"
    key = f"rate:{ip}:{int(datetime.now(UTC).timestamp() // settings.RATE_LIMIT_WINDOW_SECONDS)}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
    if count > settings.RATE_LIMIT_REQUESTS:
        raise RateLimitError()


async def auth_rate_limit(
    request: Request,
    redis: RedisDep,
) -> None:
    """Stricter rate limit for auth endpoints."""
    from app.core.config import settings

    ip = request.client.host if request.client else "unknown"
    key = f"rate:auth:{ip}:{int(datetime.now(UTC).timestamp() // settings.AUTH_RATE_LIMIT_WINDOW_SECONDS)}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, settings.AUTH_RATE_LIMIT_WINDOW_SECONDS)
    if count > settings.AUTH_RATE_LIMIT_REQUESTS:
        raise RateLimitError()
