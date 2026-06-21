"""Unit tests for OTPService — QR OTP generate / consume.

Written TDD-style; tests are expected to FAIL until OTPService is
implemented in a later F03 task.

Uses ``fakeredis`` so no real Redis instance is needed.

Refs: Design §6.1, AC-F03-1, AC-F03-4, AC-F03-6
"""

import fakeredis
import pytest

from app.services.otp_service import (
    OTPExpiredError,
    OTPUsedError,
    consume_otp,
    generate_otp,
)

OTP_TTL = 300
INITIATOR_ID = "user-initiator-uuid"


@pytest.fixture()
def redis_client() -> fakeredis.FakeRedis:
    """Return an isolated fakeredis instance per test."""
    return fakeredis.FakeRedis(decode_responses=True)


def test_generate_returns_valid_token(
    redis_client: fakeredis.FakeRedis,
) -> None:
    """Token is a valid UUID; TTL is set to ~300 s in Redis."""
    import uuid

    result = generate_otp(redis_client, INITIATOR_ID)

    # token must be a parseable UUID
    uuid.UUID(result["token"])

    key = f"qr_otp:{result['token']}"
    assert redis_client.exists(key)
    ttl = redis_client.ttl(key)
    assert 0 < ttl <= OTP_TTL


def test_consume_valid_otp(redis_client: fakeredis.FakeRedis) -> None:
    """Consuming a fresh OTP returns initiator_id and marks it used."""
    result = generate_otp(redis_client, INITIATOR_ID)
    token = result["token"]

    consumed = consume_otp(redis_client, token)

    assert consumed["initiator_id"] == INITIATOR_ID
    # Key should still exist but marked used=true
    import json

    key = f"qr_otp:{token}"
    raw = redis_client.get(key)
    data = json.loads(raw)
    assert data["used"] is True


def test_consume_expired_otp(redis_client: fakeredis.FakeRedis) -> None:
    """Consuming a non-existent (expired) key raises OTPExpiredError."""
    with pytest.raises(OTPExpiredError):
        consume_otp(redis_client, "nonexistent-token")


def test_consume_used_otp(redis_client: fakeredis.FakeRedis) -> None:
    """Consuming an already-used OTP raises OTPUsedError."""
    result = generate_otp(redis_client, INITIATOR_ID)
    token = result["token"]

    consume_otp(redis_client, token)  # first use

    with pytest.raises(OTPUsedError):
        consume_otp(redis_client, token)  # second use


def test_consume_race_condition(redis_client: fakeredis.FakeRedis) -> None:
    """Simulated double-consume: only first succeeds, second raises.

    NOTE: True concurrency cannot be tested in a single-threaded unit
    test with fakeredis; this test verifies the sequential idempotency
    of the consume logic. Race-condition safety comes from the Lua
    script in the real implementation (Design §2.3).
    """
    result = generate_otp(redis_client, INITIATOR_ID)
    token = result["token"]

    first = consume_otp(redis_client, token)
    assert first["initiator_id"] == INITIATOR_ID

    with pytest.raises(OTPUsedError):
        consume_otp(redis_client, token)
