"""Firebase Admin SDK singleton initialisation (optional).

When ``AUTH_MODE=jwt`` or when ``FIREBASE_CREDENTIALS_JSON`` is absent,
Firebase is treated as unavailable.  All callers must guard FCM/auth
calls with :func:`is_firebase_available`.

Refs: Design §4, AC-F12-1, AC-F12-5, DL-F12-01
"""

import json
import logging

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings

logger = logging.getLogger(__name__)

_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App | None:
    """Return (or initialise) the Firebase Admin SDK singleton.

    Returns ``None`` — without raising — when credentials are absent or
    when ``AUTH_MODE=jwt`` (standalone mode).  Callers should check
    :func:`is_firebase_available` before using Firebase APIs.

    Returns:
        Initialised ``firebase_admin.App``, or ``None``.
    """
    global _app
    if _app is not None:
        return _app

    if not settings.firebase_credentials_json:
        logger.info(
            "FIREBASE_CREDENTIALS_JSON not set — Firebase disabled"
        )
        return None

    try:
        cred = credentials.Certificate(
            json.loads(settings.firebase_credentials_json)
        )
        _app = firebase_admin.initialize_app(cred)
        return _app
    except Exception:  # noqa: BLE001
        logger.warning(
            "Firebase initialisation failed — running without Firebase",
            exc_info=True,
        )
        return None


def is_firebase_available() -> bool:
    """Return True if the Firebase Admin SDK has been initialised.

    Use this guard before any ``firebase_admin.*`` call that requires a
    live Firebase project (FCM, Auth verify, etc.).
    """
    return _app is not None
