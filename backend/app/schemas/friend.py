"""Pydantic schemas for the friends / social-graph feature (F03).

Refs: Design §3
"""

from datetime import datetime

from pydantic import BaseModel, field_validator


class GenerateQRResponse(BaseModel):
    """Response body for POST /friends/qr/generate."""

    token: str
    deep_link: str
    expires_at: str


class ScanQRRequest(BaseModel):
    """Request body for POST /friends/qr/scan."""

    token: str

    @field_validator("token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        """Reject blank token strings."""
        if not v.strip():
            raise ValueError("token must not be empty")
        return v


class FriendItem(BaseModel):
    """Single friend entry in the friend list response."""

    user_id: str
    display_name: str | None
    avatar_url: str | None
    friendship_created_at: datetime


class FriendListResponse(BaseModel):
    """Response body for GET /friends."""

    friends: list[FriendItem]
    total: int


class FriendInfo(BaseModel):
    """Minimal friend profile embedded in scan response."""

    user_id: str
    display_name: str | None
    avatar_url: str | None


class ScanQRResponse(BaseModel):
    """Response body for POST /friends/qr/scan (201 Created)."""

    friendship_id: str
    friend: FriendInfo
    created_at: datetime


class FCMTokenRequest(BaseModel):
    """Request body for PUT /friends/fcm-token.

    ``timezone`` is optional (backward-compatible, DL-F09-02).
    When present it must be a valid IANA timezone string.
    """

    fcm_token: str
    timezone: str | None = None

    @field_validator("fcm_token")
    @classmethod
    def fcm_token_not_empty(cls, v: str) -> str:
        """Reject blank FCM token strings."""
        if not v.strip():
            raise ValueError("fcm_token must not be empty")
        return v
