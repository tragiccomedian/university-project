"""Project endpoints."""

import uuid

from fastapi import APIRouter, Query, status

from app.api.v1.deps import (
    ProjectServiceDep,
    RequireAdmin,
    RequireMember,
    RequireViewer,
)
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/workspaces/{ws_id}/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead], summary="List projects in workspace")
async def list_projects(
    ctx: RequireViewer,
    service: ProjectServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ProjectRead]:
    projects, _ = await service.list_projects(ctx.workspace.id, limit=limit, offset=offset)
    return [ProjectRead.model_validate(p) for p in projects]


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project (Member+)",
)
async def create_project(
    body: ProjectCreate,
    ctx: RequireMember,
    service: ProjectServiceDep,
) -> ProjectRead:
    project = await service.create_project(ctx.workspace.id, body)
    return ProjectRead.model_validate(project)


@router.get(
    "/{proj_id}",
    response_model=ProjectRead,
    summary="Get project details (Viewer+)",
)
async def get_project(
    proj_id: uuid.UUID,
    ctx: RequireViewer,
    service: ProjectServiceDep,
) -> ProjectRead:
    project = await service.get_project(ctx.workspace.id, proj_id)
    return ProjectRead.model_validate(project)


@router.patch(
    "/{proj_id}",
    response_model=ProjectRead,
    summary="Update project (Member+)",
)
async def update_project(
    proj_id: uuid.UUID,
    body: ProjectUpdate,
    ctx: RequireMember,
    service: ProjectServiceDep,
) -> ProjectRead:
    project = await service.update_project(ctx.workspace.id, proj_id, body)
    return ProjectRead.model_validate(project)


@router.delete(
    "/{proj_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project (Admin+)",
)
async def delete_project(
    proj_id: uuid.UUID,
    ctx: RequireAdmin,
    service: ProjectServiceDep,
) -> None:
    await service.delete_project(ctx.workspace.id, proj_id)
