"""Internal JWT issuance (HS256) for upstream service forwarding.

The Internal JWT is forwarded via the ``X-Internal-Token`` header to all
protected upstream services.  Upstream services decode the payload (without
verifying the signature) to extract identity claims.

References: design.md §Internal JWT Claims, FR-02.3, FR-02.4.
"""

from datetime import UTC, datetime, timedelta

import jwt

_ISSUER = "dokat-api-gateway"
_ALGORITHM = "HS256"


def extract_auth_provider(firebase_claims: dict) -> str:
    """Return the internal ``auth_provider`` string from Firebase claims.

    Maps ``firebase.sign_in_provider`` to the value stored in the Internal
    JWT.  Unknown providers are forwarded as-is (design.md §Firebase Token →
    auth_provider mapping).

    Args:
        firebase_claims: Decoded Firebase ID Token claims dict.

    Returns:
        Provider string (e.g. ``'google.com'``, ``'anonymous'``).
        Falls back to ``'unknown'`` when the key is absent.
    """
    firebase_info = firebase_claims.get("firebase", {})
    return firebase_info.get("sign_in_provider", "unknown")


def issue_internal_jwt(
    uid: str,
    email: str | None,
    auth_provider: str,
    secret_key: str,
    expiry_minutes: int = 15,
) -> str:
    """Sign and return an Internal JWT for forwarding to upstream services.

    The token is signed with HS256 using ``secret_key`` (``JWT_SECRET_KEY``).
    Upstream services decode the payload without verifying the signature,
    relying on the gateway's network trust boundary.

    Args:
        uid: Firebase UID — used for both ``uid`` and ``sub`` claims.
        email: User email address, or ``None`` for anonymous users.
        auth_provider: Provider string (e.g. ``'google.com'``,
            ``'anonymous'``).
        secret_key: HS256 signing key from ``Settings.jwt_secret_key``.
        expiry_minutes: Token validity window in minutes (default: 15).

    Returns:
        Signed JWT string.
    """
    now = datetime.now(UTC)
    payload: dict = {
        "uid": uid,
        "email": email,
        "auth_provider": auth_provider,
        "iat": now,
        "exp": now + timedelta(minutes=expiry_minutes),
        "iss": _ISSUER,
        "sub": uid,
    }
    return jwt.encode(payload, secret_key, algorithm=_ALGORITHM)
