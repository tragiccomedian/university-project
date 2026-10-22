"""Task endpoints with optimistic locking and filtering."""

import uuid

from fastapi import APIRouter, Query, status

from app.api.v1.deps import (
    RequireMember,
    RequireViewer,
    TaskServiceDep,
)
from app.schemas.base import PaginatedResponse
from app.schemas.task import (
    TaskCreate,
    TaskDetail,
    TaskFilterParams,
    TaskPriority,
    TaskRead,
    TaskStatus,
    TaskUpdate,
)

router = APIRouter(prefix="/workspaces/{ws_id}/tasks", tags=["tasks"])


class PaginatedTaskResponse(PaginatedResponse):
    items: list[TaskRead]


@router.get("", response_model=PaginatedTaskResponse, summary="List tasks with filters and search")
async def list_tasks(
    ctx: RequireViewer,
    service: TaskServiceDep,
    project_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    search: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginatedTaskResponse:
    params = TaskFilterParams(
        project_id=project_id,
        assignee_id=assignee_id,
        status=status,
        priority=priority,
        search=search,
        limit=limit,
        offset=offset,
    )
    items, total = await service.list_tasks(ctx.workspace.id, params)
    return PaginatedTaskResponse(
        items=[TaskRead.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
        has_next=(offset + limit < total),
    )


@router.post(
    "",
    response_model=TaskDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task (Member+)",
)
async def create_task(
    body: TaskCreate,
    ctx: RequireMember,
    service: TaskServiceDep,
) -> TaskDetail:
    task = await service.create_task(ctx.workspace.id, ctx.user, body)
    return TaskDetail.model_validate(task)


@router.get(
    "/{task_id}",
    response_model=TaskDetail,
    summary="Get task details and subtasks (Viewer+)",
)
async def get_task(
    task_id: uuid.UUID,
    ctx: RequireViewer,
    service: TaskServiceDep,
) -> TaskDetail:
    task = await service.get_task(ctx.workspace.id, task_id)
    return TaskDetail.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskDetail,
    summary="Update task with optimistic locking (Member+)",
    responses={
        409: {"description": "Version conflict: task was concurrently modified"},
        422: {"description": "Cyclic subtask loop or invalid assignee"},
    },
)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    ctx: RequireMember,
    service: TaskServiceDep,
) -> TaskDetail:
    updated = await service.update_task(ctx.workspace.id, task_id, ctx.user, body)
    return TaskDetail.model_validate(updated)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task (Member+)",
)
async def delete_task(
    task_id: uuid.UUID,
    ctx: RequireMember,
    service: TaskServiceDep,
) -> None:
    await service.delete_task(ctx.workspace.id, task_id, ctx.user)


@router.post(
    "/{task_id}/labels/{label_id}",
    response_model=TaskDetail,
    summary="Attach a label to task (Member+)",
)
async def add_label(
    task_id: uuid.UUID,
    label_id: uuid.UUID,
    ctx: RequireMember,
    service: TaskServiceDep,
) -> TaskDetail:
    task = await service.add_label_to_task(ctx.workspace.id, task_id, label_id)
    return TaskDetail.model_validate(task)


@router.delete(
    "/{task_id}/labels/{label_id}",
    response_model=TaskDetail,
    summary="Detach a label from task (Member+)",
)
async def remove_label(
    task_id: uuid.UUID,
    label_id: uuid.UUID,
    ctx: RequireMember,
    service: TaskServiceDep,
) -> TaskDetail:
    task = await service.remove_label_from_task(ctx.workspace.id, task_id, label_id)
    return TaskDetail.model_validate(task)
