"""Activity log endpoints."""

import uuid

from fastapi import APIRouter, Query

from app.api.v1.deps import DbDep, RequireViewer
from app.repositories.activity_log import ActivityLogRepository
from app.schemas.activity_log import ActivityLogRead

router = APIRouter(tags=["activity log"])


@router.get(
    "/workspaces/{ws_id}/activity",
    response_model=list[ActivityLogRead],
    summary="Get activity audit log for workspace",
)
async def get_workspace_activity(
    ctx: RequireViewer,
    session: DbDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ActivityLogRead]:
    repo = ActivityLogRepository(session)
    logs = await repo.list_by_workspace(ctx.workspace.id, limit=limit, offset=offset)
    return [ActivityLogRead.model_validate(l) for l in logs]


@router.get(
    "/workspaces/{ws_id}/tasks/{task_id}/activity",
    response_model=list[ActivityLogRead],
    summary="Get activity audit log for task",
)
async def get_task_activity(
    task_id: uuid.UUID,
    ctx: RequireViewer,
    session: DbDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ActivityLogRead]:
    repo = ActivityLogRepository(session)
    logs = await repo.list_by_entity("task", task_id, limit=limit, offset=offset)
    return [ActivityLogRead.model_validate(l) for l in logs]
