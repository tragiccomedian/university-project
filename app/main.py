"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    configure_logging()
    logger.info("TaskFlow API starting", env=settings.DEBUG and "dev" or "prod")

    # Verify Redis connectivity on startup
    from app.db.redis import redis_client

    await redis_client.ping()
    logger.info("Redis connected")

    yield

    # Graceful shutdown
    from app.db.session import engine

    await engine.dispose()
    await redis_client.aclose()
    logger.info("TaskFlow API stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Multi-user task tracker with timelines, habits, "
            "notes, time tracking and real-time notifications."
        ),
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Static Files & Frontend ───────────────────────────────────────────────
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if not static_dir.exists():
        static_dir = Path(__file__).resolve().parent / "static"

    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_index() -> FileResponse:
            return FileResponse(static_dir / "index.html")

        @app.get("/favicon.ico", include_in_schema=False)
        async def serve_favicon() -> FileResponse:
            fav = static_dir / "favicon.svg"
            if fav.exists():
                return FileResponse(fav, media_type="image/svg+xml")
            return FileResponse(static_dir / "index.html")

    return app


app = create_app()
