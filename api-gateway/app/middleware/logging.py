"""Access logging middleware (FR-04.1, FR-04.3–04.5, AC-08).

Emits one JSON line per request to stdout via stdlib logging.
Does not log Authorization headers, Firebase tokens, or Internal JWT
payloads.
"""

import json
import logging
import time
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


def _build_log_entry(
    request: Request,
    status_code: int,
    latency_ms: float,
) -> dict:
    """Build the access log entry for a completed request.

    Args:
        request: The incoming Starlette request (reads ``request.state``).
        status_code: HTTP status code of the response.
        latency_ms: Total request latency in milliseconds.

    Returns:
        Dict with all required access log fields (FR-04.1).
    """
    auth = getattr(request.state, "auth", None)
    route = getattr(request.state, "route", None)
    client = request.client

    return {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "trace_id": getattr(request.state, "trace_id", ""),
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
        "upstream_latency_ms": getattr(
            request.state, "upstream_latency_ms", None
        ),
        "user_id": auth.uid if auth else None,
        "client_ip": client.host if client else None,
        "upstream": route.upstream_url if route else None,
        "route_id": route.route_id if route else None,
    }


class AccessLoggingMiddleware(BaseHTTPMiddleware):
    """Log JSON access entries after each request completes."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        latency_ms = (time.monotonic() - start) * 1000.0
        entry = _build_log_entry(request, response.status_code, latency_ms)
        message = json.dumps(entry)

        if response.status_code >= 500:
            logger.error(message)
        else:
            logger.info(message)

        return response
