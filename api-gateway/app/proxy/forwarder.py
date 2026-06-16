"""HTTP proxy forwarder: build upstream request and measure latency."""

import time
from dataclasses import dataclass

import httpx
from starlette.requests import Request

from app.auth.dependency import AuthContext
from app.errors.codes import ErrorCode
from app.errors.handlers import GatewayError
from app.proxy.headers import build_upstream_headers, strip_hop_by_hop_headers
from app.routing.registry import RouteConfig


@dataclass(frozen=True)
class ForwardResult:
    """Result of a successful upstream proxy call.

    Attributes:
        status_code: HTTP status code from upstream.
        body: Raw response body bytes.
        headers: Response headers (hop-by-hop stripped).
        upstream_latency_ms: Round-trip latency to upstream in milliseconds.
    """

    status_code: int
    body: bytes
    headers: dict[str, str]
    upstream_latency_ms: float


def _build_upstream_url(route: RouteConfig, request: Request) -> str:
    """Build the full upstream URL from route base and request path."""
    base = route.upstream_url.rstrip("/")
    path = request.url.path
    url = f"{base}{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    return url


def _strip_response_headers(headers: httpx.Headers) -> dict[str, str]:
    """Return response headers with hop-by-hop entries removed."""
    return strip_hop_by_hop_headers(dict(headers))


async def forward_request(
    request: Request,
    route: RouteConfig,
    auth_ctx: AuthContext,
    http_client: httpx.AsyncClient,
    trace_id: str,
) -> ForwardResult:
    """Forward the incoming request to the upstream service.

    Args:
        request: Incoming Starlette request.
        route: Matched route configuration.
        auth_ctx: Authenticated user context with Internal JWT.
        http_client: Shared httpx async client.
        trace_id: Request trace identifier.

    Returns:
        ``ForwardResult`` with passthrough status, body, and headers.

    Raises:
        GatewayError: ``UPSTREAM_TIMEOUT`` (502) or
            ``UPSTREAM_UNAVAILABLE`` (503) on transport failures.
    """
    upstream_url = _build_upstream_url(route, request)
    body = await request.body()
    headers = build_upstream_headers(
        dict(request.headers),
        auth_ctx.internal_jwt,
        trace_id,
    )

    start = time.monotonic()
    try:
        response = await http_client.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            content=body if body else None,
        )
    except httpx.TimeoutException as exc:
        raise GatewayError(
            code=ErrorCode.UPSTREAM_TIMEOUT,
            message="Upstream service did not respond in time.",
            status_code=502,
        ) from exc
    except httpx.ConnectError as exc:
        raise GatewayError(
            code=ErrorCode.UPSTREAM_UNAVAILABLE,
            message="Upstream service is unavailable.",
            status_code=503,
        ) from exc

    latency_ms = (time.monotonic() - start) * 1000.0

    return ForwardResult(
        status_code=response.status_code,
        body=response.content,
        headers=_strip_response_headers(response.headers),
        upstream_latency_ms=latency_ms,
    )
