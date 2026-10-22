"""Health-check endpoints.

/health/live  → liveness: app process is running (always 200 if reachable)
/health/ready → readiness: DB and Redis are reachable (200 or 503)

Used by Docker HEALTHCHECK and Kubernetes probes.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.redis import redis_client
from app.db.session import engine

router = APIRouter(tags=["health"])


@router.get(
    "/health/live",
    summary="Liveness probe",
    description="Returns 200 if the application process is running.",
)
async def liveness() -> dict:
    return {"status": "ok"}


@router.get(
    "/health/ready",
    summary="Readiness probe",
    description="Returns 200 when both PostgreSQL and Redis are reachable.",
)
async def readiness() -> JSONResponse:
    checks: dict[str, str] = {}
    healthy = True

    # PostgreSQL check
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"
        healthy = False

    # Redis check
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        healthy = False

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )
