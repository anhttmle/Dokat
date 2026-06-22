"""Pydantic schemas for the settings feature (F10).

Refs: Design §2.4, §3
"""

from datetime import datetime

from pydantic import BaseModel, field_validator


class BlockRequest(BaseModel):
    """Request body for POST /users/block."""

    user_id: str

    @field_validator("user_id")
    @classmethod
    def user_id_not_empty(cls, v: str) -> str:
        """Reject blank user_id strings."""
        if not v.strip():
            raise ValueError("user_id must not be empty")
        return v


class ReportRequest(BaseModel):
    """Request body for POST /users/report."""

    user_id: str
    reason: str

    @field_validator("user_id", "reason")
    @classmethod
    def not_empty(cls, v: str) -> str:
        """Reject blank values."""
        if not v.strip():
            raise ValueError("value must not be empty")
        return v


class BlockedUserItem(BaseModel):
    """Single entry in the blocked-users list response."""

    user_id: str
    display_name: str | None
    avatar_url: str | None
    blocked_at: datetime


class BlockListResponse(BaseModel):
    """Response body for GET /users/block."""

    blocked: list[BlockedUserItem]
    total: int
