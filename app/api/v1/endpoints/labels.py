"""Label endpoints."""

import uuid

from fastapi import APIRouter, status

from app.api.v1.deps import DbDep, RequireAdmin, RequireMember, RequireViewer
from app.core.errors import ConflictError, NotFoundError
from app.repositories.label import LabelRepository
from app.schemas.label import LabelCreate, LabelRead

router = APIRouter(prefix="/workspaces/{ws_id}/labels", tags=["labels"])


@router.get("", response_model=list[LabelRead], summary="List workspace labels")
async def list_labels(
    ctx: RequireViewer,
    session: DbDep,
) -> list[LabelRead]:
    repo = LabelRepository(session)
    labels = await repo.list_by_workspace(ctx.workspace.id)
    return [LabelRead.model_validate(l) for l in labels]


@router.post(
    "",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new label (Member+)",
)
async def create_label(
    body: LabelCreate,
    ctx: RequireMember,
    session: DbDep,
) -> LabelRead:
    repo = LabelRepository(session)
    existing = await repo.get_by_name(ctx.workspace.id, body.name)
    if existing:
        raise ConflictError(f"Label '{body.name}' already exists in this workspace.")

    label = await repo.create(
        workspace_id=ctx.workspace.id,
        name=body.name,
        color=body.color,
    )
    return LabelRead.model_validate(label)


@router.delete(
    "/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a label (Admin+)",
)
async def delete_label(
    label_id: uuid.UUID,
    ctx: RequireAdmin,
    session: DbDep,
) -> None:
    repo = LabelRepository(session)
    label = await repo.get(label_id)
    if not label or label.workspace_id != ctx.workspace.id:
        raise NotFoundError("Label not found.")
    await repo.delete(label)
