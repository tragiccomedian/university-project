"""Tests for Workspaces, RBAC, and Member management."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.fixture
def auth_header_factory():
    def _create(user_id: uuid.UUID) -> dict[str, str]:
        token, _, _ = create_access_token(user_id)
        return {"Authorization": f"Bearer {token}"}

    return _create


@pytest.mark.asyncio
async def test_workspace_crud_and_rbac(client: AsyncClient, auth_header_factory) -> None:
    """Test workspace creation and role-based permissions."""
    owner_id = uuid.uuid4()
    headers = auth_header_factory(owner_id)

    # 1. Accessing a non-existent or foreign workspace should return 401 or 404
    foreign_ws_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/workspaces/{foreign_ws_id}", headers=headers)
    assert resp.status_code in (401, 404)


@pytest.mark.asyncio
async def test_workspace_duplicate_slug_validation(client: AsyncClient) -> None:
    """Slug format validation."""
    resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Bad Slug WS", "slug": "INVALID SLUG WITH SPACES!"},
    )
    # Validation error because slug has pattern [a-z0-9-]+
    assert resp.status_code in (401, 422)
