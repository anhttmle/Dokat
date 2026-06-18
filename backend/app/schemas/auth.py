"""Pydantic schemas for authentication endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """Response body for POST /auth/session."""

    user_id: uuid.UUID
    firebase_uid: str
    is_anonymous: bool
    force_link_required: bool
    force_link_at: datetime | None
    providers: list[str]


class LinkResponse(BaseModel):
    """Response body for POST /auth/link."""

    user_id: uuid.UUID
    is_anonymous: bool
    providers: list[str]
    merged: bool = False
