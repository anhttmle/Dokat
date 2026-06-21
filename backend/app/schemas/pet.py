"""Pydantic schemas for pet profile endpoints."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator

from app.models.pet_profile import PetGender, PetSpecies


class PetResponse(BaseModel):
    """Response body for a single pet profile."""

    id: uuid.UUID
    name: str
    species: PetSpecies
    gender: PetGender
    birthdate: date | None
    avatar_url: str | None
    created_at: datetime


class PetListResponse(BaseModel):
    """Response body for GET /pets."""

    pets: list[PetResponse]


class CreatePetRequest(BaseModel):
    """Request body for POST /pets."""

    name: str
    species: PetSpecies
    gender: PetGender = PetGender.unknown
    birthdate: date | None = None
    avatar_url: str | None = None

    @field_validator("birthdate")
    @classmethod
    def birthdate_not_in_future(
        cls, v: date | None
    ) -> date | None:
        """Reject birthdate values that are in the future."""
        if v is not None and v > date.today():
            raise ValueError("birthdate cannot be in the future")
        return v


class PatchPetRequest(BaseModel):
    """Request body for PATCH /pets/{pet_id} (partial update)."""

    name: str | None = None
    species: PetSpecies | None = None
    gender: PetGender | None = None
    birthdate: date | None = None
    avatar_url: str | None = None


class LinkPhotoRequest(BaseModel):
    """Request body for PATCH /pets/{pet_id}/link-photo."""

    photo_id: uuid.UUID


class LinkPhotoResponse(BaseModel):
    """Response body for PATCH /pets/{pet_id}/link-photo."""

    pet_id: uuid.UUID
    photo_id: uuid.UUID
    linked_at: datetime


class PetPhotoItem(BaseModel):
    """Single photo entry in a pet timeline."""

    photo_id: uuid.UUID
    cdn_url: str
    taken_at: datetime | None


class PetPhotosResponse(BaseModel):
    """Response body for GET /pets/{pet_id}/photos."""

    pet_id: uuid.UUID
    photos: list[PetPhotoItem]
    next_cursor: str | None
    has_more: bool
