"""Parallel upstream health probes (FR-06, AC-07, D-03, D-09)."""

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.routing.registry import RouteConfig

_SERVICE_KEYS: dict[str, str] = {
    "users": "user-service",
    "pets": "pet-service",
    "posts": "post-service",
    "feed": "feed-service",
    "social": "social-service",
    "capture": "capture-service",
    "send": "send-service",
    "view": "view-service",
    "responses": "response-service",
    "history": "history-service",
    "onboarding": "onboarding-service",
    "notifications": "notification-service",
    "settings": "setting-service",
    "ai": "ai-service",
}


@dataclass(frozen=True)
class UpstreamProbeResult:
    """Result of probing one upstream ``GET /health`` endpoint."""

    status: str
    latency_ms: int | None
    error: str | None = None


async def _probe_one(
    client: httpx.AsyncClient,
    base_url: str,
    timeout: float,
) -> UpstreamProbeResult:
    """Probe ``GET {base_url}/health`` with the given timeout."""
    url = f"{base_url.rstrip('/')}/health"
    start = time.monotonic()
    try:
        response = await client.get(url, timeout=timeout)
        latency_ms = int((time.monotonic() - start) * 1000.0)
        if response.status_code < 400:
            return UpstreamProbeResult(status="up", latency_ms=latency_ms)
        return UpstreamProbeResult(
            status="down",
            latency_ms=latency_ms,
            error=f"HTTP {response.status_code}",
        )
    except httpx.TimeoutException:
        return UpstreamProbeResult(
            status="down",
            latency_ms=None,
            error="timeout",
        )
    except httpx.ConnectError as exc:
        return UpstreamProbeResult(
            status="down",
            latency_ms=None,
            error=str(exc) or "connection refused",
        )


def _probe_result_to_dict(result: UpstreamProbeResult) -> dict:
    """Convert probe result to the health response upstream entry."""
    entry: dict = {
        "status": result.status,
        "latency_ms": result.latency_ms,
    }
    if result.error is not None:
        entry["error"] = result.error
    return entry


async def run_health_check(
    route_table: list[RouteConfig],
    http_client: httpx.AsyncClient,
    timeout_seconds: int,
) -> tuple[dict, int]:
    """Probe all upstream services and build the health response.

    Args:
        route_table: Gateway route table with upstream URLs.
        http_client: Shared async HTTP client.
        timeout_seconds: Per-probe timeout (D-09).

    Returns:
        Tuple of (response body dict, HTTP status code).
    """
    url_to_routes: dict[str, list[RouteConfig]] = {}
    for route in route_table:
        url_to_routes.setdefault(route.upstream_url, []).append(route)

    unique_urls = list(url_to_routes.keys())
    timeout = float(timeout_seconds)
    probe_tasks = [
        _probe_one(http_client, url, timeout) for url in unique_urls
    ]
    probe_results = await asyncio.gather(*probe_tasks)

    url_results = dict(zip(unique_urls, probe_results, strict=True))

    upstreams: dict[str, dict] = {}
    any_non_critical_down = False
    any_critical_down = False

    for route in route_table:
        service_key = _SERVICE_KEYS[route.route_id]
        result = url_results[route.upstream_url]
        upstreams[service_key] = _probe_result_to_dict(result)
        if result.status == "down":
            if route.is_critical:
                any_critical_down = True
            else:
                any_non_critical_down = True

    if any_critical_down:
        overall_status = "unhealthy"
        http_status = 503
    elif any_non_critical_down:
        overall_status = "degraded"
        http_status = 200
    else:
        overall_status = "healthy"
        http_status = 200

    body = {
        "status": overall_status,
        "gateway": "ok",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "upstreams": upstreams,
    }
    return body, http_status
