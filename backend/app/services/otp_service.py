"""OTP service — generate and atomically consume QR OTP tokens.

Each token is stored in Redis under ``qr_otp:{token}`` as JSON
with a TTL of 300 seconds.  A Lua script ensures check-and-mark-
used is atomic, preventing race conditions when two scanners use
the same OTP simultaneously (Design §2.3).

Refs: Design §1.1, §1.2, §2.3, §3.1, §3.2
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import redis.asyncio

from app.core.config import settings
from app.schemas.friend import GenerateQRResponse

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


@dataclass
class OTPPayload:
    """Payload returned by ``OTPService.consume``."""

    initiator_id: str


def _otp_key(token: str) -> str:
    return f"qr_otp:{token}"


class OTPService:
    """Async service for generating and consuming QR OTP tokens.

    Args:
        redis_client: An async Redis (or fakeredis) client with
            ``decode_responses=True``.

    Refs: Design §2.3
    """

    def __init__(self, redis_client: redis.asyncio.Redis) -> None:
        self._redis = redis_client

    async def generate(self, initiator_id: str) -> GenerateQRResponse:
        """Create a new QR OTP token and store it in Redis.

        Args:
            initiator_id: UUID string of the user generating the QR.

        Returns:
            ``GenerateQRResponse`` with ``token``, ``deep_link``,
            and ``expires_at``.
        """
        token = str(uuid.uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=OTP_TTL_SECONDS)

        payload = json.dumps(
            {
                "initiator_id": initiator_id,
                "created_at": now.isoformat(),
                "used": False,
            }
        )
        await self._redis.set(_otp_key(token), payload, ex=OTP_TTL_SECONDS)

        deep_link = f"{settings.deep_link_base}/add-friend?token={token}"
        return GenerateQRResponse(
            token=token,
            deep_link=deep_link,
            expires_at=expires_at.isoformat(),
        )

    async def consume(self, token: str) -> OTPPayload:
        """Atomically consume an OTP token using a Lua script.

        Args:
            token: UUID token string extracted from the deep link.

        Returns:
            ``OTPPayload`` with ``initiator_id``.

        Raises:
            OTPExpiredError: Key does not exist (expired or invalid).
            OTPUsedError: Token was already consumed.
        """
        key = _otp_key(token)
        result = await self._redis.eval(_LUA_CONSUME, 1, key)

        raw, status = result[0], result[1]

        if status == "expired":
            raise OTPExpiredError(
                f"OTP {token!r} has expired or does not exist"
            )
        if status == "used":
            raise OTPUsedError(f"OTP {token!r} has already been used")

        data = json.loads(raw)
        return OTPPayload(initiator_id=data["initiator_id"])
