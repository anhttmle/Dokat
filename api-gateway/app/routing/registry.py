"""Route registry: maps path prefixes to upstream service configuration.

Each entry is a ``RouteConfig`` dataclass. The table is built once at
startup from the application ``Settings`` and passed to the matcher.

Critical upstream classification follows D-03:
  Critical  : users, pets, onboarding  → health check returns 503 if down
  Non-critical: all others             → health check returns 200 (degraded)
"""

from dataclasses import dataclass

_CRITICAL_ROUTE_IDS = frozenset({"users", "pets", "onboarding"})
_CAPTURE_ROUTE_ID = "capture"
_AI_ROUTE_ID = "ai"


@dataclass(frozen=True)
class RouteConfig:
    """Immutable configuration for one proxied route.

    Attributes:
        prefix: URL path prefix (e.g. ``"/pets"``).
        route_id: Short stable identifier used in rate-limit keys and logs.
        upstream_url: Base URL of the upstream service (no trailing slash).
        is_critical: Whether this upstream is critical for the health check.
        is_ai: Whether this route proxies to a third-party AI provider
            (D-07 — forwards ``AI_API_KEY`` instead of ``X-Internal-Token``).
        rate_limit_per_min: Per-route request limit per user per minute.
            ``None`` means the global user limit applies unchanged.
    """

    prefix: str
    route_id: str
    upstream_url: str
    is_critical: bool = False
    is_ai: bool = False
    rate_limit_per_min: int | None = None


_DEFAULT_CAPTURE_LIMIT = 20  # FR-03.3, D-05


def build_route_table(
    upstream_urls: dict[str, str],
    capture_rate_limit_per_min: int = _DEFAULT_CAPTURE_LIMIT,
) -> list[RouteConfig]:
    """Build the full route table from a mapping of route_id → upstream URL.

    Args:
        upstream_urls: Dict mapping route_id (e.g. ``"pets"``) to the
            upstream base URL (e.g. ``"http://pet-svc:8000"``).

    Returns:
        List of ``RouteConfig`` objects ordered by prefix length descending
        so the matcher can iterate and return the first match.
    """
    route_defs: list[tuple[str, str]] = [
        ("/users", "users"),
        ("/pets", "pets"),
        ("/posts", "posts"),
        ("/feed", "feed"),
        ("/social", "social"),
        ("/capture", "capture"),
        ("/send", "send"),
        ("/view", "view"),
        ("/responses", "responses"),
        ("/history", "history"),
        ("/onboarding", "onboarding"),
        ("/notifications", "notifications"),
        ("/settings", "settings"),
        ("/ai", "ai"),
    ]

    routes: list[RouteConfig] = []
    for prefix, route_id in route_defs:
        url = upstream_urls.get(route_id, "")
        routes.append(
            RouteConfig(
                prefix=prefix,
                route_id=route_id,
                upstream_url=url,
                is_critical=route_id in _CRITICAL_ROUTE_IDS,
                is_ai=route_id == _AI_ROUTE_ID,
                rate_limit_per_min=(
                    capture_rate_limit_per_min
                    if route_id == _CAPTURE_ROUTE_ID
                    else None
                ),
            )
        )

    # Longest prefix first so the matcher short-circuits correctly.
    routes.sort(key=lambda r: len(r.prefix), reverse=True)
    return routes
