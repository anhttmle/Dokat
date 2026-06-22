"""Pets router: CRUD, avatar upload-url, link-photo, and timeline."""

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.routers.auth import get_db
from app.schemas.pet import (
    CreatePetRequest,
    LinkPhotoRequest,
    LinkPhotoResponse,
    PatchPetRequest,
    PetListResponse,
    PetPhotosResponse,
    PetResponse,
)
from app.schemas.profile import PresignedUrlRequest, PresignedUrlResponse
from app.services import pet_service, storage_service

router = APIRouter(prefix="/pets", tags=["pets"])


@router.get("", response_model=PetListResponse)
def list_pets(
    request: Request,
    db: Session = Depends(get_db),
) -> PetListResponse:
    """List all pet profiles owned by the user."""
    firebase_uid: str = request.state.firebase_uid
    return PetListResponse(pets=pet_service.list_pets(db, firebase_uid))


@router.post("", response_model=PetResponse, status_code=201)
def create_pet(
    request: Request,
    payload: CreatePetRequest,
    db: Session = Depends(get_db),
) -> PetResponse | JSONResponse:
    """Create a new pet profile (enforces the per-user limit)."""
    firebase_uid: str = request.state.firebase_uid
    try:
        return pet_service.create_pet(db, firebase_uid, payload)
    except pet_service.PetLimitReachedError:
        return JSONResponse(
            status_code=403,
            content={
                "error": "PET_LIMIT_REACHED",
                "message": "Free users can only have 1 pet profile.",
            },
        )


@router.post("/avatar/upload-url", response_model=PresignedUrlResponse)
def create_avatar_upload_url(
    request: Request,
    payload: PresignedUrlRequest,
) -> PresignedUrlResponse | JSONResponse:
    """Return a presigned S3 PUT URL for a pet avatar.

    Object key uses user_id (not pet_id) since pet doesn't exist
    yet at upload time (DL-F02-04).

    Returns:
        ``PresignedUrlResponse`` on success (200).
        JSON 400 with ``INVALID_CONTENT_TYPE`` for unsupported MIME types.
    """
    firebase_uid: str = request.state.firebase_uid
    try:
        return storage_service.generate_upload_url(
            user_id=firebase_uid,
            prefix="avatars/pets",
            content_type=payload.content_type,
        )
    except storage_service.InvalidContentTypeError:
        return JSONResponse(
            status_code=400,
            content={
                "error": "INVALID_CONTENT_TYPE",
                "message": "Unsupported content type.",
            },
        )


@router.get("/{pet_id}", response_model=PetResponse)
def get_pet(
    request: Request,
    pet_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PetResponse | JSONResponse:
    """Return a single pet profile owned by the user."""
    firebase_uid: str = request.state.firebase_uid
    try:
        return pet_service.get_pet(db, firebase_uid, pet_id)
    except pet_service.PetNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "error": "PET_NOT_FOUND",
                "message": "Pet not found.",
            },
        )


@router.patch("/{pet_id}", response_model=PetResponse)
def patch_pet(
    request: Request,
    pet_id: uuid.UUID,
    payload: PatchPetRequest,
    db: Session = Depends(get_db),
) -> PetResponse | JSONResponse:
    """Apply a partial update to a pet profile."""
    firebase_uid: str = request.state.firebase_uid
    try:
        return pet_service.patch_pet(db, firebase_uid, pet_id, payload)
    except pet_service.PetNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "error": "PET_NOT_FOUND",
                "message": "Pet not found.",
            },
        )


@router.patch("/{pet_id}/link-photo", response_model=LinkPhotoResponse)
def link_photo(
    request: Request,
    pet_id: uuid.UUID,
    payload: LinkPhotoRequest,
    db: Session = Depends(get_db),
) -> LinkPhotoResponse | JSONResponse:
    """Link a feed photo to a pet profile."""
    firebase_uid: str = request.state.firebase_uid
    try:
        return pet_service.link_photo(
            db, firebase_uid, pet_id, payload.photo_id
        )
    except pet_service.PetNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "error": "PET_NOT_FOUND",
                "message": "Pet or photo not found.",
            },
        )
    except pet_service.PhotoAlreadyLinkedError:
        return JSONResponse(
            status_code=409,
            content={
                "error": "PHOTO_ALREADY_LINKED",
                "message": "Photo is already linked to a pet.",
            },
        )


@router.get("/{pet_id}/photos", response_model=PetPhotosResponse)
def get_pet_photos(
    request: Request,
    pet_id: uuid.UUID,
    limit: int = 20,
    before: str | None = None,
    db: Session = Depends(get_db),
) -> PetPhotosResponse | JSONResponse:
    """Return a cursor-paginated timeline of a pet's photos."""
    firebase_uid: str = request.state.firebase_uid
    try:
        return pet_service.get_pet_photos(
            db, firebase_uid, pet_id, limit, before
        )
    except pet_service.PetNotFoundError:
        return JSONResponse(
            status_code=404,
            content={
                "error": "PET_NOT_FOUND",
                "message": "Pet not found.",
            },
        )
