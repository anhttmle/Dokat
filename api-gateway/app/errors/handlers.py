"""Global exception handlers and the GatewayError domain exception.

Registers three handlers on the FastAPI application:

* ``GatewayError``   — domain errors raised by gateway middleware/routes.
* ``HTTPException``  — FastAPI / Starlette HTTP errors (overrides default
                       ``{"detail": ...}`` format with our schema).
* ``Exception``      — catch-all for unexpected runtime errors → HTTP 500.
                       Stack trace is logged but NEVER returned to the client
                       (FR-05.5).
"""

import logging
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.errors.codes import ErrorCode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exception
# ---------------------------------------------------------------------------


class GatewayError(Exception):
    """Raised by gateway middleware and handlers for known error conditions."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Schema helper
# ---------------------------------------------------------------------------


def error_response(
    code: ErrorCode | str,
    message: str,
    trace_id: str,
) -> dict:
    """Build the canonical FR-05.1 error body.

    Args:
        code: An ``ErrorCode`` member or plain string for ad-hoc codes.
        message: Human-readable description shown to the client.
        trace_id: Request trace identifier forwarded to the client so that
            support can correlate the error with server-side logs.

    Returns:
        A dict suitable for use as a ``JSONResponse`` body.
    """
    return {
        "error": {
            "code": str(code),
            "message": message,
            "trace_id": trace_id,
        }
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _trace_id(request: Request) -> str:
    """Extract trace_id from request state; fall back to empty string.

    The trace middleware (T-03) populates ``request.state.trace_id``.
    This fallback prevents errors during the transition period.
    """
    return getattr(request.state, "trace_id", "")


# ---------------------------------------------------------------------------
# Handler functions
# ---------------------------------------------------------------------------


async def _handle_gateway_error(
    request: Request, exc: GatewayError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.code, exc.message, _trace_id(request)),
    )


async def _handle_http_exception(
    request: Request, exc: HTTPException
) -> JSONResponse:
    detail = str(exc.detail) if exc.detail else "An error occurred."
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            f"HTTP_{exc.status_code}", detail, _trace_id(request)
        ),
    )


async def _handle_unhandled_exception(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler — logs the full stack trace, hides it from client."""
    logger.error(
        "Unhandled exception: %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content=error_response(
            ErrorCode.INTERNAL_ERROR,
            "An internal error occurred.",
            _trace_id(request),
        ),
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all gateway exception handlers to *app*.

    Call once inside ``create_app()`` after constructing the FastAPI instance.
    """
    _handlers: list[tuple[type[Exception], Callable]] = [
        (GatewayError, _handle_gateway_error),
        (HTTPException, _handle_http_exception),
        (Exception, _handle_unhandled_exception),
    ]
    for exc_type, handler in _handlers:
        app.add_exception_handler(exc_type, handler)
