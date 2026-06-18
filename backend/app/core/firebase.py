"""Firebase Admin SDK singleton initialisation."""

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings

_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App:
    """Return (or initialise) the Firebase Admin SDK singleton.

    Uses the credentials file path from Settings. In tests,
    firebase_admin.auth.verify_id_token is mocked so this is
    never called with a real credentials file.
    """
    global _app
    if _app is not None:
        return _app

    if settings.firebase_credentials_path:
        cred = credentials.Certificate(settings.firebase_credentials_path)
    else:
        cred = credentials.ApplicationDefault()

    _app = firebase_admin.initialize_app(cred)
    return _app
