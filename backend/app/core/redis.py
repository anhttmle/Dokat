"""Redis client singleton for the application.

Provides a module-level ``get_redis_client()`` factory that returns a
``redis.Redis`` instance configured from environment variables.

In tests, callers should pass a ``fakeredis.FakeRedis`` instance
directly to the service functions instead of using this factory.

Refs: Design §2.3
"""

import redis

from app.core.config import settings


def get_redis_client() -> redis.Redis:
    """Return a Redis client connected to the configured URL.

    The client uses ``decode_responses=True`` so all keys and values
    are returned as ``str`` rather than ``bytes``.
    """
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
