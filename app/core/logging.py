"""Structured JSON logging via structlog."""

import logging
import sys

import structlog

from app.core.config import settings


def _add_logger_name_safe(
    logger: object, method_name: str, event_dict: dict[str, object]
) -> dict[str, object]:
    if hasattr(logger, "name"):
        event_dict["logger"] = logger.name
    return event_dict


def configure_logging() -> None:
    """Set up structlog with JSON output in prod and pretty-print in dev."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_logger_name_safe,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.DEBUG:
        # Human-readable in dev
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        # JSON in production
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging to pipe into structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[return-value]
