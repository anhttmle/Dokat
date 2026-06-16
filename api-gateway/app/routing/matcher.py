"""Route matcher: longest-prefix match against the route table.

The route table is pre-sorted longest-prefix-first by ``build_route_table``,
so the first match found is always the most specific one.
"""

from app.routing.registry import RouteConfig


def match_route(path: str, routes: list[RouteConfig]) -> RouteConfig | None:
    """Return the best-matching ``RouteConfig`` for *path*, or ``None``.

    A route matches when *path* starts with ``route.prefix + "/"``.
    The table must be sorted longest-prefix-first (done by
    ``build_route_table``).

    Args:
        path: The incoming request path (e.g. ``"/pets/123"``).
        routes: Pre-sorted route table from ``build_route_table``.

    Returns:
        The first matching ``RouteConfig``, or ``None`` if no route matches.
    """
    for route in routes:
        if path.startswith(route.prefix + "/") or path == route.prefix:
            return route
    return None
