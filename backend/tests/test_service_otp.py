"""Unit tests for OTPService — QR OTP generate / consume.

Written TDD-style: tests use the async OTPService class API.
Uses ``fakeredis.aioredis`` so no real Redis instance is needed.

Refs: Design §6.1, AC-F03-1, AC-F03-4, AC-F03-6
"""

import asyncio
import uuid

import fakeredis.aioredis
import pytest

from app.services.otp_service import (
    OTPExpiredError,
    OTPService,
    OTPUsedError,
)

INITIATOR_ID = "user-initiator-uuid"


@pytest.fixture()
def redis_client() -> fakeredis.aioredis.FakeRedis:
    """Return an isolated async fakeredis instance per test."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


async def test_generate_returns_valid_token(
    redis_client: fakeredis.aioredis.FakeRedis,
) -> None:
    """Token is a valid UUID v4; TTL is set to ~300 s in Redis."""
    svc = OTPService(redis_client)
    result = await svc.generate(initiator_id=INITIATOR_ID)

    uuid.UUID(result.token)  # raises if not valid UUID

    ttl = await redis_client.ttl(f"qr_otp:{result.token}")
    assert 298 <= ttl <= 300


async def test_consume_valid_otp(
    redis_client: fakeredis.aioredis.FakeRedis,
) -> None:
    """Consuming a fresh OTP returns the correct initiator_id."""
    svc = OTPService(redis_client)
    gen = await svc.generate(initiator_id=INITIATOR_ID)

    payload = await svc.consume(gen.token)

    assert payload.initiator_id == INITIATOR_ID


async def test_consume_marks_used(
    redis_client: fakeredis.aioredis.FakeRedis,
) -> None:
    """Second consume on the same token raises OTPUsedError."""
    svc = OTPService(redis_client)
    gen = await svc.generate(initiator_id=INITIATOR_ID)
    await svc.consume(gen.token)

    with pytest.raises(OTPUsedError):
        await svc.consume(gen.token)


async def test_consume_expired_otp(
    redis_client: fakeredis.aioredis.FakeRedis,
) -> None:
    """Consuming a non-existent (expired) key raises OTPExpiredError."""
    svc = OTPService(redis_client)

    with pytest.raises(OTPExpiredError):
        await svc.consume("non-existent-token")


async def test_consume_race_condition(
    redis_client: fakeredis.aioredis.FakeRedis,
) -> None:
    """Concurrent consume: exactly one succeeds, the other raises.

    NOTE: fakeredis runs single-threaded; asyncio.gather here tests
    sequential idempotency. Real atomicity is guaranteed by the Lua
    script on a live Redis instance (Design §2.3).
    """
    svc = OTPService(redis_client)
    gen = await svc.generate(initiator_id=INITIATOR_ID)

    results = await asyncio.gather(
        svc.consume(gen.token),
        svc.consume(gen.token),
        return_exceptions=True,
    )

    ok = sum(1 for r in results if not isinstance(r, Exception))
    assert ok == 1
