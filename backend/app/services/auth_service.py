"""Business logic for authentication flows."""

from datetime import datetime, timezone

from app.models.user import User
from app.schemas.auth import SessionResponse


def _ensure_utc(dt: datetime) -> datetime:
    """Return *dt* as a UTC-aware datetime.

    SQLite returns naive datetimes; PostgreSQL returns aware ones.
    This normalises both for comparison.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def build_session_response(user: User) -> SessionResponse:
    """Build the ``SessionResponse`` for ``POST /auth/session``.

    ``force_link_required`` is ``True`` when the user is still anonymous
    *and* ``force_link_at`` is in the past (Design §3.1).

    Args:
        user: ORM ``User`` instance (providers relationship accessible).

    Returns:
        Populated ``SessionResponse``.
    """
    now = datetime.now(timezone.utc)

    force_link_at = (
        _ensure_utc(user.force_link_at) if user.force_link_at else None
    )
    force_link_required = bool(
        user.is_anonymous
        and force_link_at is not None
        and now >= force_link_at
    )

    providers = [p.provider.value for p in user.providers]

    return SessionResponse(
        user_id=user.id,
        firebase_uid=user.firebase_uid,
        is_anonymous=user.is_anonymous,
        force_link_required=force_link_required,
        force_link_at=force_link_at,
        providers=providers,
    )
