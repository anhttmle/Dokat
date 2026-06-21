"""Redis async client singleton for the application.

Provides ``get_redis_client()`` which returns a
``redis.asyncio.Redis`` instance configured from environment
variables.

In tests, inject a ``fakeredis.aioredis.FakeRedis`` instance
directly into the service constructors instead of calling this
factory.

Refs: Design §2.3
"""

import redis.asyncio

from app.core.config import settings


def get_redis_client() -> redis.asyncio.Redis:
    """Return an async Redis client connected to the configured URL.

    ``decode_responses=True`` ensures all keys and values are
    returned as ``str`` rather than ``bytes``.
    """
    return redis.asyncio.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
