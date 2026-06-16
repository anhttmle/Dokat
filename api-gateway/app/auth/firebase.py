"""Firebase ID Token verification via Firebase Admin SDK.

Exposes two public callables:
- ``init_firebase_app``: Initialise the SDK at application startup.
- ``verify_id_token``: Verify a raw Firebase ID Token string.

Both are designed to be patchable in tests (``unittest.mock.patch``).
"""

import logging
import os

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials

from app.errors.codes import ErrorCode
from app.errors.handlers import GatewayError

logger = logging.getLogger(__name__)


def init_firebase_app(credentials_path: str) -> None:
    """Initialise Firebase Admin SDK from a service-account credentials file.

    This is a no-op when:
    - The SDK is already initialised (idempotent startup).
    - The credentials file does not exist (graceful degradation in dev/test
      environments where the file is not mounted).

    Args:
        credentials_path: Filesystem path to the Firebase service-account
            JSON file (``FIREBASE_CREDENTIALS_PATH`` env var).
    """
    if firebase_admin._apps:
        return

    if not os.path.isfile(credentials_path):
        logger.warning(
            "Firebase credentials not found at '%s'; "
            "Firebase Admin SDK not initialised.",
            credentials_path,
        )
        return

    cred = credentials.Certificate(credentials_path)
    firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialised.")


def verify_id_token(token: str) -> dict:
    """Verify a Firebase ID Token and return the decoded claims dict.

    Wraps ``firebase_admin.auth.verify_id_token`` and maps SDK exceptions
    to ``GatewayError(UNAUTHORIZED)`` so callers don't depend on the
    Firebase SDK exception hierarchy.

    Args:
        token: Raw Firebase ID Token string from the Authorization header.

    Returns:
        Decoded claims dict (``uid``, ``email``, ``firebase``, …).

    Raises:
        GatewayError: ``UNAUTHORIZED`` (HTTP 401) for any token failure.
    """
    try:
        return fb_auth.verify_id_token(token, check_revoked=True)
    except fb_auth.RevokedIdTokenError as exc:
        raise GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Firebase ID token has been revoked.",
            status_code=401,
        ) from exc
    except fb_auth.ExpiredIdTokenError as exc:
        raise GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Firebase ID token has expired.",
            status_code=401,
        ) from exc
    except fb_auth.InvalidIdTokenError as exc:
        raise GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Firebase ID token is invalid.",
            status_code=401,
        ) from exc
    except Exception as exc:
        # Catches CertificateFetchError and unexpected SDK errors.
        logger.error(
            "Firebase token verification failed unexpectedly: %s", exc
        )
        raise GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Authentication failed.",
            status_code=401,
        ) from exc
