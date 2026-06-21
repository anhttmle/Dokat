"""Business logic for pet profile flows (F02)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import nullslast
from sqlalchemy.orm import Session

from app.models.pet_profile import PetProfile
from app.models.photo import Photo
from app.models.user import User
from app.schemas.pet import (
    CreatePetRequest,
    LinkPhotoResponse,
    PatchPetRequest,
    PetPhotoItem,
    PetPhotosResponse,
    PetResponse,
)

FREE_USER_PET_LIMIT = 1


class PetLimitReachedError(Exception):
    """Raised when a free user exceeds the pet profile limit."""


class PetNotFoundError(Exception):
    """Raised when a pet does not exist or is not owned by the user."""


class PhotoAlreadyLinkedError(Exception):
    """Raised when a photo is already linked to another pet."""


def assert_can_create_pet(db: Session, user_id: uuid.UUID) -> None:
    """Raise ``PetLimitReachedError`` if the user is at the pet limit.

    Args:
        db: Active SQLAlchemy session.
        user_id: Owner user UUID.
    """
    count = (
        db.query(PetProfile)
        .filter(PetProfile.user_id == user_id)
        .count()
    )
    if count >= FREE_USER_PET_LIMIT:
        raise PetLimitReachedError()


def list_pets(db: Session, firebase_uid: str) -> list[PetResponse]:
    """Return all pet profiles owned by the authenticated user.

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID from the verified ID token.
    """
    user = _get_user_or_raise(db, firebase_uid)
    pets = (
        db.query(PetProfile)
        .filter(PetProfile.user_id == user.id)
        .all()
    )
    return [_to_response(p) for p in pets]


def create_pet(
    db: Session,
    firebase_uid: str,
    payload: CreatePetRequest,
) -> PetResponse:
    """Create a new pet profile after enforcing the per-user limit.

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID from the verified ID token.
        payload: Validated request body.

    Raises:
        PetLimitReachedError: If the user already has ``FREE_USER_PET_LIMIT``
            pets.
    """
    user = _get_user_or_raise(db, firebase_uid)
    assert_can_create_pet(db, user.id)
    pet = PetProfile(
        user_id=user.id,
        name=payload.name,
        species=payload.species,
        gender=payload.gender,
        birthdate=payload.birthdate,
        avatar_url=payload.avatar_url,
    )
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return _to_response(pet)


def get_pet(
    db: Session,
    firebase_uid: str,
    pet_id: uuid.UUID,
) -> PetResponse:
    """Return a single pet profile owned by the authenticated user.

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID from the verified ID token.
        pet_id: Target pet UUID.

    Raises:
        PetNotFoundError: If the pet does not exist or belongs to another
            user.
    """
    user = _get_user_or_raise(db, firebase_uid)
    pet = (
        db.query(PetProfile)
        .filter(
            PetProfile.id == pet_id,
            PetProfile.user_id == user.id,
        )
        .first()
    )
    if pet is None:
        raise PetNotFoundError()
    return _to_response(pet)


def patch_pet(
    db: Session,
    firebase_uid: str,
    pet_id: uuid.UUID,
    payload: PatchPetRequest,
) -> PetResponse:
    """Apply a partial update to a pet profile.

    Only fields explicitly included in *payload* are written.

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID from the verified ID token.
        pet_id: Target pet UUID.
        payload: Fields to update (all optional).

    Raises:
        PetNotFoundError: If the pet does not exist or belongs to another
            user.
    """
    user = _get_user_or_raise(db, firebase_uid)
    pet = (
        db.query(PetProfile)
        .filter(
            PetProfile.id == pet_id,
            PetProfile.user_id == user.id,
        )
        .first()
    )
    if pet is None:
        raise PetNotFoundError()
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pet, field, value)
    db.commit()
    db.refresh(pet)
    return _to_response(pet)


def link_photo(
    db: Session,
    firebase_uid: str,
    pet_id: uuid.UUID,
    photo_id: uuid.UUID,
) -> LinkPhotoResponse:
    """Link a feed photo to a pet profile.

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID from the verified ID token.
        pet_id: Target pet UUID (must belong to the caller).
        photo_id: Photo UUID (must belong to the caller).

    Raises:
        PetNotFoundError: If ``pet_id`` or ``photo_id`` does not exist
            or does not belong to the caller.
        PhotoAlreadyLinkedError: If the photo already has a non-NULL
            ``pet_id`` (Design §3.9; DL-F02-05).
    """
    user = _get_user_or_raise(db, firebase_uid)
    pet = (
        db.query(PetProfile)
        .filter(
            PetProfile.id == pet_id,
            PetProfile.user_id == user.id,
        )
        .first()
    )
    if pet is None:
        raise PetNotFoundError()

    photo = (
        db.query(Photo)
        .filter(Photo.id == photo_id, Photo.user_id == user.id)
        .first()
    )
    if photo is None:
        raise PetNotFoundError()

    if photo.pet_id is not None:
        raise PhotoAlreadyLinkedError()

    photo.pet_id = pet_id
    db.commit()

    return LinkPhotoResponse(
        pet_id=pet_id,
        photo_id=photo_id,
        linked_at=datetime.now(timezone.utc),
    )


def get_pet_photos(
    db: Session,
    firebase_uid: str,
    pet_id: uuid.UUID,
    limit: int = 20,
    before: str | None = None,
) -> PetPhotosResponse:
    """Return a cursor-paginated timeline of a pet's photos.

    Photos are ordered by ``taken_at DESC`` (oldest-last), with
    ``created_at DESC`` as a tiebreaker.  Callers advance the page
    by passing the returned ``next_cursor`` value as ``before`` on
    the next request (Design §3.10; DL-F02-03).

    Args:
        db: Active SQLAlchemy session.
        firebase_uid: Firebase UID from the verified ID token.
        pet_id: Target pet UUID (must belong to the caller).
        limit: Maximum photos to return (default 20, max 50).
        before: ISO 8601 ``taken_at`` cursor; only photos *older*
            than this value are returned.

    Raises:
        PetNotFoundError: If the pet does not exist or belongs to
            another user.
    """
    user = _get_user_or_raise(db, firebase_uid)
    pet = (
        db.query(PetProfile)
        .filter(
            PetProfile.id == pet_id,
            PetProfile.user_id == user.id,
        )
        .first()
    )
    if pet is None:
        raise PetNotFoundError()

    query = db.query(Photo).filter(Photo.pet_id == pet_id)

    if before is not None:
        # URL query strings decode '+' as ' ', but ISO 8601 timezone
        # offsets use '+'.  Restore it so fromisoformat succeeds.
        normalised = before.replace(" ", "+")
        cursor_dt = datetime.fromisoformat(normalised)
        if cursor_dt.tzinfo is None:
            cursor_dt = cursor_dt.replace(tzinfo=timezone.utc)
        query = query.filter(Photo.taken_at < cursor_dt)

    query = query.order_by(
        nullslast(Photo.taken_at.desc()),
        Photo.created_at.desc(),
    )

    rows = query.limit(limit + 1).all()
    has_more = len(rows) > limit
    page = rows[:limit]

    next_cursor: str | None = None
    if has_more and page:
        last_taken_at = page[-1].taken_at
        if last_taken_at is not None:
            next_cursor = last_taken_at.isoformat()

    return PetPhotosResponse(
        pet_id=pet_id,
        photos=[
            PetPhotoItem(
                photo_id=p.id,
                cdn_url=p.cdn_url,
                taken_at=p.taken_at,
            )
            for p in page
        ],
        next_cursor=next_cursor,
        has_more=has_more,
    )


def _get_user_or_raise(db: Session, firebase_uid: str) -> User:
    """Fetch the User row or raise ValueError."""
    user = (
        db.query(User)
        .filter(User.firebase_uid == firebase_uid)
        .first()
    )
    if user is None:
        raise ValueError(f"User not found: {firebase_uid}")
    return user


def _to_response(pet: PetProfile) -> PetResponse:
    """Map a ``PetProfile`` ORM row to a ``PetResponse``."""
    return PetResponse(
        id=pet.id,
        name=pet.name,
        species=pet.species,
        gender=pet.gender,
        birthdate=pet.birthdate,
        avatar_url=pet.avatar_url,
        created_at=pet.created_at,
    )
