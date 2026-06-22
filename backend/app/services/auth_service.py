"""Business logic for authentication flows."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.user import OAuthProvider, User, UserProvider
from app.schemas.auth import LinkResponse, SessionResponse


def _ensure_utc(dt: datetime) -> datetime:
    """Return *dt* as a UTC-aware datetime.

    SQLite returns naive datetimes; PostgreSQL returns aware ones.
    This normalises both for comparison.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
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
    now = datetime.now(UTC)

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


def link_provider(
    db: Session,
    firebase_uid: str,
    provider: OAuthProvider,
    provider_uid: str,
) -> LinkResponse:
    """Link an OAuth provider to the user identified by *firebase_uid*.

    Handles three cases:
    1. New provider → insert ``UserProvider`` row, set
       ``is_anonymous=False``.
    2. Same provider already linked (idempotent) → no DB change, return
       current state.
    3. Provider belongs to another user (user B) → delete the guest
       record, return user B's data with ``merged=True``.

    Foreign-key reassignments for future tables (friends, photos) must
    be added here when those tables exist (DL-017).

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID of the requesting user.
        provider: ``OAuthProvider`` enum value.
        provider_uid: Provider-specific subject string.

    Returns:
        ``LinkResponse`` describing the resulting account state.

    Raises:
        ValueError: If no user record exists for *firebase_uid*.
    """
    current_user = (
        db.query(User).filter(User.firebase_uid == firebase_uid).first()
    )
    if current_user is None:
        raise ValueError(f"User not found for uid: {firebase_uid}")

    existing = (
        db.query(UserProvider)
        .filter(
            UserProvider.provider == provider,
            UserProvider.provider_uid == provider_uid,
        )
        .first()
    )

    merged = False

    if existing is not None and existing.user_id != current_user.id:
        # Provider belongs to another user → merge guest into that user.
        target_user_id = existing.user_id
        db.delete(current_user)
        db.commit()
        target_user = db.query(User).filter(User.id == target_user_id).one()
        merged = True
    else:
        target_user = current_user
        if existing is None:
            db.add(
                UserProvider(
                    user_id=target_user.id,
                    provider=provider,
                    provider_uid=provider_uid,
                )
            )
        target_user.is_anonymous = False
        db.commit()

    db.refresh(target_user)
    providers = [p.provider.value for p in target_user.providers]

    return LinkResponse(
        user_id=target_user.id,
        is_anonymous=target_user.is_anonymous,
        providers=providers,
        merged=merged,
    )
