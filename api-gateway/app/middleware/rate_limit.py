"""Redis sliding-window rate limiting (FR-03, AC-03, AC-04, AC-10)."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.auth.dependency import get_settings
from app.config import Settings
from app.errors.codes import ErrorCode
from app.errors.handlers import GatewayError, gateway_error_response
from app.routing.registry import RouteConfig

WINDOW_SECONDS = 60


def compute_retry_after(ttl_seconds: int) -> int:
    """Return Retry-After seconds from Redis TTL (minimum 1s, FR-03.5)."""
    return max(1, ttl_seconds)


async def check_limit(redis, key: str, limit: int) -> tuple[bool, int]:
    """Increment counter and check against limit.

    Uses INCR + EXPIRE sliding window counter (design §Redis Key Schema).

    Args:
        redis: Async Redis client.
        key: Redis key for this limit bucket.
        limit: Maximum requests allowed per window.

    Returns:
        Tuple of (allowed, retry_after). retry_after is 0 when allowed.
    """
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, WINDOW_SECONDS)

    ttl = await redis.ttl(key)
    if ttl < 0:
        await redis.expire(key, WINDOW_SECONDS)
        ttl = WINDOW_SECONDS

    if count > limit:
        return False, compute_retry_after(ttl)
    return True, 0


def rate_limit_error(retry_after: int) -> GatewayError:
    """Build a 429 GatewayError with Retry-After header."""
    return GatewayError(
        code=ErrorCode.RATE_LIMIT_EXCEEDED,
        message=f"Too many requests. Retry after {retry_after} seconds.",
        status_code=429,
        headers={"Retry-After": str(retry_after)},
    )


async def _enforce_limit(redis, key: str, limit: int) -> None:
    """Raise rate_limit_error when the limit is exceeded."""
    allowed, retry_after = await check_limit(redis, key, limit)
    if not allowed:
        raise rate_limit_error(retry_after)


def _client_ip(request: Request) -> str:
    """Return client IP from the direct connection (D-08)."""
    if request.client is None:
        return "unknown"
    return request.client.host


async def check_ip_limit(redis, client_ip: str, settings: Settings) -> None:
    """Enforce per-IP rate limit for public endpoints (FR-03.2)."""
    await _enforce_limit(
        redis,
        f"rl:ip:{client_ip}",
        settings.rate_limit_ip_per_min,
    )


async def check_protected_limits(
    redis,
    uid: str,
    route: RouteConfig,
    settings: Settings,
) -> None:
    """Enforce global, per-user, and per-route limits (FR-03)."""
    global_limit = settings.rate_limit_global_per_min
    await _enforce_limit(redis, "rl:global", global_limit)
    await _enforce_limit(
        redis,
        f"rl:user:{uid}",
        settings.rate_limit_user_per_min,
    )
    if route.rate_limit_per_min is not None:
        await _enforce_limit(
            redis,
            f"rl:route:{uid}:{route.route_id}",
            route.rate_limit_per_min,
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP rate limit for public routes; protected limits run after auth."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/health":
            redis = request.app.state.redis
            settings = get_settings()
            try:
                await check_ip_limit(redis, _client_ip(request), settings)
            except GatewayError as exc:
                return gateway_error_response(request, exc)

        return await call_next(request)
