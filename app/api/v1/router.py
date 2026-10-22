"""Central API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1.endpoints.activity import router as activity_router
from app.api.v1.endpoints.attachments import router as attachments_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.comments import router as comments_router
from app.api.v1.endpoints.habits import router as habits_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.labels import router as labels_router
from app.api.v1.endpoints.milestones import router as milestones_router
from app.api.v1.endpoints.notes import router as notes_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.search import router as search_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.time_entries import router as time_entries_router
from app.api.v1.endpoints.websocket import router as websocket_router
from app.api.v1.endpoints.workspaces import router as workspaces_router

api_router = APIRouter()

# Health checks (sit at root for Docker/k8s probes)
api_router.include_router(health_router)

# Versioned domain routes (/api/v1)
api_router.include_router(auth_router, prefix="/api/v1")
api_router.include_router(workspaces_router, prefix="/api/v1")
api_router.include_router(projects_router, prefix="/api/v1")
api_router.include_router(tasks_router, prefix="/api/v1")
api_router.include_router(labels_router, prefix="/api/v1")
api_router.include_router(comments_router, prefix="/api/v1")
api_router.include_router(milestones_router, prefix="/api/v1")
api_router.include_router(time_entries_router, prefix="/api/v1")
api_router.include_router(habits_router, prefix="/api/v1")
api_router.include_router(notes_router, prefix="/api/v1")
api_router.include_router(attachments_router, prefix="/api/v1")
api_router.include_router(activity_router, prefix="/api/v1")
api_router.include_router(search_router, prefix="/api/v1")
api_router.include_router(notifications_router, prefix="/api/v1")
api_router.include_router(websocket_router, prefix="/api/v1")
