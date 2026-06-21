"""Owner profile router: GET/PATCH /profile/me and avatar upload-url."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.routers.auth import get_db
from app.schemas.profile import (
    OwnerProfileResponse,
    PatchOwnerProfileRequest,
    PresignedUrlRequest,
    PresignedUrlResponse,
)
from app.services import profile_service, storage_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=OwnerProfileResponse)
def get_me(
    request: Request,
    db: Session = Depends(get_db),
) -> OwnerProfileResponse:
    """Return the authenticated user's owner profile."""
    firebase_uid: str = request.state.firebase_uid
    return profile_service.get_owner_profile(db, firebase_uid)


@router.patch("/me", response_model=OwnerProfileResponse)
def patch_me(
    request: Request,
    payload: PatchOwnerProfileRequest,
    db: Session = Depends(get_db),
) -> OwnerProfileResponse:
    """Apply a partial update to the owner profile."""
    firebase_uid: str = request.state.firebase_uid
    return profile_service.update_owner_profile(db, firebase_uid, payload)


@router.post("/me/avatar/upload-url", response_model=PresignedUrlResponse)
def create_avatar_upload_url(
    request: Request,
    payload: PresignedUrlRequest,
) -> PresignedUrlResponse | JSONResponse:
    """Return a presigned S3 PUT URL for the owner avatar.

    Returns:
        ``PresignedUrlResponse`` on success (200).
        JSON 400 with ``INVALID_CONTENT_TYPE`` for unsupported MIME types.
    """
    firebase_uid: str = request.state.firebase_uid
    try:
        return storage_service.generate_upload_url(
            user_id=firebase_uid,
            prefix="avatars/users",
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
