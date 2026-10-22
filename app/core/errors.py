"""Centralised error handling and uniform error response format.

All API errors follow the envelope:
    {
        "error": {
            "code": "SNAKE_CASE_CODE",
            "message": "Human-readable message",
            "details": { ... }   # optional
        }
    }
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Error body schemas ────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


# ── Domain exceptions ─────────────────────────────────────────────────────────


class AppError(Exception):
    """Base class for all application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        self.message = message or self.__class__.message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "Resource not found."


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action."


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AUTHENTICATION_FAILED"
    message = "Authentication failed."


class TokenExpiredError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "TOKEN_EXPIRED"
    message = "Access token has expired."


class TokenRevokedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "TOKEN_REVOKED"
    message = "Token has been revoked."


class TokenInvalidError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "TOKEN_INVALID"
    message = "Token is invalid."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "ALREADY_EXISTS"
    message = "Resource already exists."


class VersionConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "VERSION_CONFLICT"
    message = "Resource was modified concurrently. Please refresh and try again."


class TimerAlreadyRunningError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "TIMER_ALREADY_RUNNING"
    message = "You already have an active timer. Stop it before starting a new one."


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "VALIDATION_ERROR"
    message = "Validation failed."


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later."


class LastOwnerError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "LAST_OWNER"
    message = "Cannot remove or demote the last owner of a workspace."


class CyclicDependencyError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "CYCLIC_DEPENDENCY"
    message = "This change would create a cyclic dependency."


# ── Exception handlers ────────────────────────────────────────────────────────


def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message, getattr(exc, "details", None))


def _validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "VALIDATION_ERROR",
        "Request validation failed.",
        details,
    )


def _unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Log the exception — in real middleware we'd capture this via structlog
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR",
        "An unexpected error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""
    app.add_exception_handler(AppError, _app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_error_handler)  # type: ignore[arg-type]
