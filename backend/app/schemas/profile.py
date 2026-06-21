"""Pydantic schemas for owner profile endpoints."""

import uuid

from pydantic import BaseModel


class OwnerProfileResponse(BaseModel):
    """Response body for GET/PATCH /profile/me."""

    user_id: uuid.UUID
    display_name: str | None
    avatar_url: str | None
    is_anonymous: bool
    providers: list[str]


class PatchOwnerProfileRequest(BaseModel):
    """Request body for PATCH /profile/me (partial update)."""

    display_name: str | None = None
    avatar_url: str | None = None


class PresignedUrlRequest(BaseModel):
    """Request body for avatar upload-url endpoints."""

    content_type: str


class PresignedUrlResponse(BaseModel):
    """Response body for avatar upload-url endpoints."""

    upload_url: str
    object_key: str
    cdn_url: str
    expires_in: int
