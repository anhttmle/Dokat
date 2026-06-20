"""Firebase Admin SDK singleton initialisation."""

import json

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings

_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App:
    """Return (or initialise) the Firebase Admin SDK singleton.

    Reads service-account credentials from the
    ``FIREBASE_CREDENTIALS_JSON`` environment variable (JSON string).
    Falls back to Application Default Credentials when the variable is
    not set (e.g. running on GCP with a service account attached).

    In tests, ``firebase_admin.auth.verify_id_token`` is mocked so this
    function is never called with real credentials.
    """
    global _app
    if _app is not None:
        return _app

    if settings.firebase_credentials_json:
        cred = credentials.Certificate(
            json.loads(settings.firebase_credentials_json)
        )
    else:
        cred = credentials.ApplicationDefault()

    _app = firebase_admin.initialize_app(cred)
    return _app
