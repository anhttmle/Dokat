"""Trace ID middleware (FR-04.2, AC-09, D-10).

For every incoming request:

1. Inspect the ``X-Trace-ID`` header.
2. If the value is a well-formed UUID (any version), keep it unchanged.
3. Otherwise generate a fresh UUID v4.
4. Store the trace_id on ``request.state.trace_id`` so that downstream
   middleware, route handlers, and exception handlers can read it without
   needing to re-parse headers.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_TRACE_HEADER = "X-Trace-ID"


def is_valid_uuid_v4(value: object) -> bool:
    """Return True if *value* is a canonically formatted UUID string.

    Requires the hyphenated form ``xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx``
    (36 characters). Accepts any UUID version and any case. Non-string
    inputs (including ``None``) return ``False``.

    Args:
        value: The candidate value to test.

    Returns:
        ``True`` when *value* is a valid, hyphenated UUID string.
    """
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def _resolve_trace_id(request: Request) -> str:
    """Return the client-supplied trace_id or generate a new UUID v4.

    Args:
        request: The incoming Starlette request.

    Returns:
        A UUID string to use as the trace_id for this request.
    """
    candidate = request.headers.get(_TRACE_HEADER, "")
    if is_valid_uuid_v4(candidate):
        return candidate
    return str(uuid.uuid4())


class TraceMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that populates ``request.state.trace_id``.

    Must be the outermost middleware so that the trace_id is available to
    all subsequent middleware and exception handlers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.trace_id = _resolve_trace_id(request)
        return await call_next(request)
