"""Stable HTTP error responses for the SuperMedicine Web API."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any
from uuid import uuid4


logger = logging.getLogger(__name__)


@dataclass
class APIError(Exception):
    """An expected API failure with a public, stable representation."""

    status_code: int
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


def api_error_response(exc: APIError, *, request_id: str | None = None) -> Any:
    """Build the shared JSON response for an expected API error."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "ok": False,
            "data": None,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "request_id": request_id or str(uuid4()),
        },
    )


def install_api_error_handlers(app: Any) -> None:
    """Install the shared handler without importing FastAPI at package import time."""
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(APIError)
    async def _handle_api_error(request: Request, exc: APIError) -> Any:
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        return api_error_response(exc, request_id=request_id)

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> Any:
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        issues = [
            {
                "location": [str(item) for item in error.get("loc", ())],
                "message": str(error.get("msg", "Invalid request")),
                "type": str(error.get("type", "validation_error")),
            }
            for error in exc.errors()
        ]
        return api_error_response(
            APIError(
                422,
                "request_validation_failed",
                "Request validation failed",
                details={"issues": issues},
            ),
            request_id=request_id,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> Any:
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        return api_error_response(
            APIError(exc.status_code, "http_error", str(exc.detail)),
            request_id=request_id,
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_exception(request: Request, exc: Exception) -> Any:
        request_id = getattr(request.state, "request_id", None) or str(uuid4())
        logger.exception("Unhandled Web API error request_id=%s", request_id, exc_info=exc)
        return api_error_response(
            APIError(500, "internal_error", "Internal server error"),
            request_id=request_id,
        )
