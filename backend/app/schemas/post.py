"""Pydantic schemas for the posts endpoints (F05).

``CreatePostRequest`` validates the coordinate ranges supplied by F11
(DL-F05-06). De-duplication of ``recipient_ids`` and the friend check
happen in the service layer, not here, to keep the schema declarative.

Refs: Design §2.3, §3.2; DL-F05-06; F11 §3.1, AC-F11-3
"""

import uuid

from pydantic import BaseModel, Field


class PostUploadUrlRequest(BaseModel):
    """Request body for POST /posts/upload-url."""

    content_type: str


class CreatePostRequest(BaseModel):
    """Request body for POST /posts.

    ``recipient_ids`` may be empty (FR-4). ``latitude``/``longitude`` are
    optional; when present they must fall within valid coordinate ranges
    (F11 §3.1) or Pydantic raises a 422.
    """

    s3_key: str = Field(min_length=1)
    cdn_url: str = Field(min_length=1)
    recipient_ids: list[uuid.UUID] = Field(default_factory=list)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class CreatePostResponse(BaseModel):
    """Response body for POST /posts (no latitude/longitude — AC-F11-3)."""

    post_id: uuid.UUID
    expires_at: str
    recipient_count: int
    created_at: str
