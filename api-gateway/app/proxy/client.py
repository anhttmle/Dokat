"""httpx AsyncClient pool lifecycle for upstream proxy requests."""

import httpx


async def create_http_client(timeout_seconds: float) -> httpx.AsyncClient:
    """Create a shared async HTTP client for upstream forwarding.

    Args:
        timeout_seconds: Request timeout applied to all upstream calls.

    Returns:
        Configured ``httpx.AsyncClient`` instance.
    """
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds))


async def close_http_client(client: httpx.AsyncClient) -> None:
    """Close the shared async HTTP client.

    Args:
        client: Client created by :func:`create_http_client`.
    """
    await client.aclose()
