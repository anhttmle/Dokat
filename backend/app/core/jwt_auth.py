"""JWT token creation and verification for standalone auth mode.

Used when ``AUTH_MODE=jwt``.  Tokens are HS256-signed with
``JWT_SECRET_KEY`` and carry ``sub=<device_id>``.

Refs: Design §4, DL-F12-02
"""

from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings


class JWTAuthError(Exception):
    """Raised when a JWT cannot be verified."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def create_token(sub: str) -> str:
    """Issue a signed JWT for the given subject (device_id).

    Args:
        sub: Subject claim — typically the ``device_id`` string.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(tz=UTC)
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_token(token: str) -> str:
    """Decode and validate a JWT, returning the subject claim.

    Args:
        token: Raw JWT string from the ``Authorization: Bearer`` header.

    Returns:
        The ``sub`` claim (device_id).

    Raises:
        JWTAuthError: With a reason string for any validation failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise JWTAuthError("expired")
    except jwt.InvalidTokenError as exc:
        raise JWTAuthError(str(exc))

    sub: str | None = payload.get("sub")
    if not sub:
        raise JWTAuthError("missing sub claim")
    return sub
