"""Upstream header stripping and injection for proxy forwarding."""

_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "transfer-encoding",
        "te",
        "trailer",
        "upgrade",
        "proxy-authenticate",
        "proxy-authorization",
        "proxy-connection",
    }
)

_STRIP_HEADERS = frozenset({"authorization", "host"})


def build_upstream_headers(
    original: dict[str, str],
    internal_jwt: str,
    trace_id: str,
) -> dict[str, str]:
    """Build headers to send to an internal upstream service.

    Strips client ``Authorization``, original ``Host``, and hop-by-hop
    headers.  Adds ``X-Internal-Token`` and ``X-Trace-ID``.

    Args:
        original: Incoming request headers (case-insensitive keys).
        internal_jwt: Signed Internal JWT for the authenticated user.
        trace_id: Request trace identifier.

    Returns:
        Header dict suitable for the upstream httpx request.
    """
    result: dict[str, str] = {}
    for key, value in original.items():
        lower = key.lower()
        if lower in _STRIP_HEADERS or lower in _HOP_BY_HOP:
            continue
        result[key] = value

    result["X-Internal-Token"] = f"Bearer {internal_jwt}"
    result["X-Trace-ID"] = trace_id
    return result


def build_ai_upstream_headers(
    original: dict[str, str],
    ai_api_key: str,
    trace_id: str,
) -> dict[str, str]:
    """Build headers to send to a third-party AI upstream (D-07).

    Strips client ``Authorization``, original ``Host``, and hop-by-hop
    headers.  Adds provider ``Authorization: Bearer <AI_API_KEY>`` and
    ``X-Trace-ID``.  Does **not** add ``X-Internal-Token``.

    Args:
        original: Incoming request headers (case-insensitive keys).
        ai_api_key: Third-party AI provider API key.
        trace_id: Request trace identifier.

    Returns:
        Header dict suitable for the upstream httpx request.
    """
    result: dict[str, str] = {}
    for key, value in original.items():
        lower = key.lower()
        if lower in _STRIP_HEADERS or lower in _HOP_BY_HOP:
            continue
        result[key] = value

    result["Authorization"] = f"Bearer {ai_api_key}"
    result["X-Trace-ID"] = trace_id
    return result


def strip_hop_by_hop_headers(headers: dict[str, str]) -> dict[str, str]:
    """Remove hop-by-hop headers from a header dict."""
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in _HOP_BY_HOP
    }
