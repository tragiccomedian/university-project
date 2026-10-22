"""Global search endpoint."""

import uuid

from fastapi import APIRouter, Query

from app.api.v1.deps import CurrentUser, SearchServiceDep
from app.schemas.search import SearchResponse, SearchType

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Global full-text search across accessible tasks and notes",
)
async def global_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search term"),
    type: SearchType = Query(default="all", description="Entity type filter"),
    workspace_id: uuid.UUID | None = Query(default=None, description="Optional workspace scope"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = None,  # type: ignore[assignment]
    service: SearchServiceDep = None,  # type: ignore[assignment]
) -> SearchResponse:
    return await service.search(
        user=current_user,
        query_text=q,
        search_type=type,
        workspace_id=workspace_id,
        limit=limit,
    )
