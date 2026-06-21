"""Business logic for pet profile flows (F02)."""

import uuid

from sqlalchemy.orm import Session

from app.models.pet_profile import PetProfile
from app.models.user import User
from app.schemas.pet import (
    CreatePetRequest,
    LinkPhotoResponse,
    PatchPetRequest,
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
    """Link a feed photo to a pet profile."""
    raise NotImplementedError


def get_pet_photos(
    db: Session,
    firebase_uid: str,
    pet_id: uuid.UUID,
    limit: int = 20,
    before: str | None = None,
) -> PetPhotosResponse:
    """Return a cursor-paginated timeline of a pet's photos."""
    raise NotImplementedError


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
