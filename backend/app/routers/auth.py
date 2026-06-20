"""Auth router: POST /auth/session."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.schemas.auth import SessionResponse
from app.services.auth_service import build_session_response
from app.services.user_service import get_or_create_user

router = APIRouter(prefix="/auth", tags=["auth"])

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
