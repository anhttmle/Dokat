"""Auth router: POST /auth/session and POST /auth/link."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.user import OAuthProvider
from app.schemas.auth import LinkResponse, SessionResponse
from app.services.auth_service import build_session_response, link_provider
from app.services.user_service import get_or_create_user

router = APIRouter(prefix="/auth", tags=["auth"])

_PROVIDER_MAP: dict[str, OAuthProvider] = {
    "google.com": OAuthProvider.google,
    "apple.com": OAuthProvider.apple,
    "facebook.com": OAuthProvider.facebook,
}

_engine = None
_session_factory = None


def _sync_db_url() -> str:
    """Convert asyncpg URL to psycopg2-compatible sync URL."""
    return settings.database_url.replace("+asyncpg", "")


def _get_session_factory() -> sessionmaker:
    """Lazily create and cache the sync session factory."""
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_engine(_sync_db_url())
        _session_factory = sessionmaker(bind=_engine)
    return _session_factory


def get_db():
    """FastAPI dependency: yield a sync database session.

    Overridden in tests via ``app.dependency_overrides``.
    """
    factory = _get_session_factory()
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


@router.post("/session", response_model=SessionResponse)
def session(
    request: Request,
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Create or restore a user session.

    Reads ``firebase_uid`` injected by ``FirebaseAuthMiddleware`` and
    upserts the user record before returning the session payload.
    """
    firebase_uid: str = request.state.firebase_uid
    user = get_or_create_user(db, firebase_uid)
    return build_session_response(user)


@router.post("/link", response_model=LinkResponse)
def link(
    request: Request,
    db: Session = Depends(get_db),
) -> LinkResponse | JSONResponse:
    """Link an OAuth provider to the authenticated user.

    Reads ``firebase_uid`` and ``token_claims`` injected by
    ``FirebaseAuthMiddleware``.  Extracts the provider from
    ``token_claims["firebase"]["sign_in_provider"]``.

    Returns:
        ``LinkResponse`` on success.
        JSON 422 with ``AUTH_PROVIDER_NOT_FOUND`` if the token carries
        no OAuth provider identity.
    """
    firebase_uid: str = request.state.firebase_uid
    token_claims: dict = request.state.token_claims

    firebase_data: dict = token_claims.get("firebase", {})
    sign_in_provider: str = firebase_data.get(
        "sign_in_provider", "anonymous"
    )
    identities: dict = firebase_data.get("identities", {})

    provider = _PROVIDER_MAP.get(sign_in_provider)
    provider_uid_list = identities.get(sign_in_provider, [])

    if provider is None or not provider_uid_list:
        return JSONResponse(
            status_code=422,
            content={
                "error": "AUTH_PROVIDER_NOT_FOUND",
                "message": (
                    "Token does not contain a linked OAuth provider"
                ),
            },
        )

    provider_uid: str = provider_uid_list[0]
    return link_provider(db, firebase_uid, provider, provider_uid)
