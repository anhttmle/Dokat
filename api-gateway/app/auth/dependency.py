"""Auth dependency: verify Firebase token and issue Internal JWT.

Exposes:
- ``AuthContext``: Dataclass holding resolved identity for a request.
- ``get_settings``: FastAPI dependency for ``Settings`` (overridable in tests).
- ``authenticate_request``: Pure function — extract token, verify, issue JWT.
"""

from dataclasses import dataclass
from functools import lru_cache

from app.auth import firebase as _firebase_module
from app.auth.jwt_issuer import extract_auth_provider, issue_internal_jwt
from app.config import Settings
from app.errors.codes import ErrorCode
from app.errors.handlers import GatewayError


@dataclass(frozen=True)
class AuthContext:
    """Resolved authentication context attached to ``request.state.auth``.

    Attributes:
        uid: Firebase UID of the authenticated user.
        email: User email address (``None`` for anonymous users).
        auth_provider: Provider string (e.g. ``'google.com'``,
            ``'anonymous'``).
        internal_jwt: Signed Internal JWT for forwarding via
            ``X-Internal-Token``.
    """

    uid: str
    email: str | None
    auth_provider: str
    internal_jwt: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application Settings singleton.

    Uses ``lru_cache`` so Settings is created once per process.
    Override in tests via ``app.dependency_overrides[get_settings]``.
    """
    return Settings()


def authenticate_request(
    authorization_header: str,
    settings: Settings,
) -> AuthContext:
    """Verify the Firebase Bearer token and return an ``AuthContext``.

    Extracts the raw token from the ``Authorization: Bearer <token>`` header,
    verifies it with Firebase Admin SDK (via
    :func:`app.auth.firebase.verify_id_token`),
    and issues an Internal JWT.

    Args:
        authorization_header: Raw value of the ``Authorization`` header
            (e.g. ``'Bearer eyJh...'``).
        settings: Application settings for JWT signing configuration.

    Returns:
        ``AuthContext`` with uid, email, auth_provider, and internal_jwt.

    Raises:
        GatewayError: ``UNAUTHORIZED`` (HTTP 401) when the header is missing,
            malformed, or the token is invalid/expired/revoked.
    """
    if not authorization_header.lower().startswith("bearer "):
        raise GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Authorization header with Bearer token is required.",
            status_code=401,
        )

    token = authorization_header[len("bearer ") :].strip()
    if not token:
        raise GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Authorization header with Bearer token is required.",
            status_code=401,
        )

    claims = _firebase_module.verify_id_token(token)
    uid: str = claims["uid"]
    email: str | None = claims.get("email") or None
    auth_provider = extract_auth_provider(claims)
    internal_jwt = issue_internal_jwt(
        uid=uid,
        email=email,
        auth_provider=auth_provider,
        secret_key=settings.jwt_secret_key,
        expiry_minutes=settings.jwt_expiry_minutes,
    )
    return AuthContext(
        uid=uid,
        email=email,
        auth_provider=auth_provider,
        internal_jwt=internal_jwt,
    )
