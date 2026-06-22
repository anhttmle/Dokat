"""Business logic for owner profile flows (F02)."""

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.profile import OwnerProfileResponse, PatchOwnerProfileRequest


def get_owner_profile(db: Session, firebase_uid: str) -> OwnerProfileResponse:
    """Return the owner profile for the authenticated user.

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID from the verified ID token.

    Returns:
        Populated ``OwnerProfileResponse``.

    Raises:
        ValueError: If no user record exists for *firebase_uid*.
    """
    user = _get_user_or_raise(db, firebase_uid)
    return _to_response(user)


def update_owner_profile(
    db: Session,
    firebase_uid: str,
    payload: PatchOwnerProfileRequest,
) -> OwnerProfileResponse:
    """Apply a partial update to the owner profile.

    Only fields explicitly set in *payload* are written; unset
    fields (``None`` by Pydantic default) are left unchanged.

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID from the verified ID token.
        payload: Fields to update.

    Returns:
        The updated ``OwnerProfileResponse``.

    Raises:
        ValueError: If no user record exists for *firebase_uid*.
    """
    user = _get_user_or_raise(db, firebase_uid)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return _to_response(user)


def autofill_from_oauth(
    db: Session,
    firebase_uid: str,
    display_name: str | None,
    avatar_url: str | None,
) -> None:
    """Fill profile fields from OAuth token only when they are NULL.

    Called after a successful OAuth link (POST /auth/link).  Does NOT
    overwrite values the user has already set.

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID of the linked user.
        display_name: Provider display name from the Firebase token.
        avatar_url: Provider photo URL from the Firebase token.
    """
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user is None:
        return

    changed = False
    if user.display_name is None and display_name:
        user.display_name = display_name
        changed = True
    if user.avatar_url is None and avatar_url:
        user.avatar_url = avatar_url
        changed = True
    if changed:
        db.commit()


def _get_user_or_raise(db: Session, firebase_uid: str) -> User:
    """Fetch the user or raise ValueError."""
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user is None:
        raise ValueError(f"User not found: {firebase_uid}")
    return user


def _to_response(user: User) -> OwnerProfileResponse:
    """Map a ``User`` ORM row to an ``OwnerProfileResponse``."""
    providers = [p.provider.value for p in user.providers]
    return OwnerProfileResponse(
        user_id=user.id,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_anonymous=user.is_anonymous,
        providers=providers,
    )
