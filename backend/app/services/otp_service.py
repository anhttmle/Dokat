"""OTP service — generate and atomically consume QR OTP tokens.

Each token is stored in Redis under ``qr_otp:{token}`` as JSON with
a TTL of 300 seconds.  A Lua script ensures check-and-mark-used is
atomic, preventing race conditions when two scanners use the same OTP
simultaneously (Design §2.3).

Refs: Design §1.1, §1.2, §2.3, §3.1, §3.2
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import redis as _redis

from app.core.config import settings

OTP_TTL_SECONDS = 300

_LUA_CONSUME = """
local raw = redis.call('GET', KEYS[1])
if not raw then return {false, 'expired'} end
local data = cjson.decode(raw)
if data.used then return {false, 'used'} end
data.used = true
local ttl = redis.call('TTL', KEYS[1])
if ttl > 0 then
    redis.call('SET', KEYS[1], cjson.encode(data), 'EX', ttl)
end
return {raw, 'ok'}
"""


class OTPExpiredError(Exception):
    """Raised when the OTP key does not exist in Redis (expired)."""


class OTPUsedError(Exception):
    """Raised when the OTP has already been consumed."""


def _otp_key(token: str) -> str:
    return f"qr_otp:{token}"


def generate_otp(
    redis_client: _redis.Redis,
    initiator_id: str,
) -> dict:
    """Create a new QR OTP and store it in Redis.

    Args:
        redis_client: Redis (or fakeredis) client instance.
        initiator_id: UUID string of the user generating the QR.

    Returns:
        Dict with keys ``token``, ``deep_link``, ``expires_at``.
    """
    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)

    payload = json.dumps(
        {
            "initiator_id": initiator_id,
            "created_at": now.isoformat(),
            "used": False,
        }
    )
    redis_client.set(_otp_key(token), payload, ex=OTP_TTL_SECONDS)

    deep_link = (
        f"{settings.deep_link_base}/add-friend?token={token}"
    )

    return {
        "token": token,
        "deep_link": deep_link,
        "expires_at": expires_at.isoformat(),
    }


def consume_otp(
    redis_client: _redis.Redis,
    token: str,
) -> dict:
    """Atomically consume an OTP token, returning its payload.

    Uses a Lua script to ensure the check-and-mark-used operation is
    atomic on a real Redis instance (Design §2.3).  For ``fakeredis``
    (used in tests), the Lua script is evaluated directly.

    Args:
        redis_client: Redis (or fakeredis) client instance.
        token: UUID token string extracted from the deep link.

    Returns:
        Dict with key ``initiator_id``.

    Raises:
        OTPExpiredError: If the key does not exist (expired or invalid).
        OTPUsedError: If the token has already been used.
    """
    key = _otp_key(token)
    result = redis_client.eval(_LUA_CONSUME, 1, key)

    raw, status = result[0], result[1]

    if status == "expired":
        raise OTPExpiredError(f"OTP {token!r} has expired or does not exist")
    if status == "used":
        raise OTPUsedError(f"OTP {token!r} has already been used")

    data = json.loads(raw)
    return {"initiator_id": data["initiator_id"]}
