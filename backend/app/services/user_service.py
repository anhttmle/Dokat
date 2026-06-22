"""CRUD operations for users and user_providers tables."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.user import User

_FORCE_LINK_DAYS = 7


def get_or_create_user(db: Session, firebase_uid: str) -> User:
    """Return existing user or create a new anonymous one.

    For new users, ``force_link_at`` is set to
    ``created_at + 7 days`` (Design §2.1).

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID from the verified ID token.

    Returns:
        The existing or newly created ``User`` instance.
    """
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user is not None:
        return user

    now = datetime.now(UTC)
    user = User(
        firebase_uid=firebase_uid,
        is_anonymous=True,
        created_at=now,
        updated_at=now,
        force_link_at=now + timedelta(days=_FORCE_LINK_DAYS),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
