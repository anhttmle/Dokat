"""Pydantic schemas for the feed endpoint (F06).

``FeedItemResponse`` mirrors the client ``FeedItem`` type (Design §2.1):
absolute ``created_at`` (ISO 8601) is formatted to a relative string on
the client (DL-F06-07). ``FeedResponse`` wraps the page plus an opaque
``next_cursor`` (DL-F06-08).

Refs: Design §2.1, §3.1, §4.1
"""

from pydantic import BaseModel


class FeedItemResponse(BaseModel):
    """A single received post on the viewer's feed."""

    post_id: str
    sender_id: str
    sender_display_name: str | None
    sender_avatar_url: str | None
    pet_name: str | None
    cdn_url: str
    created_at: str
    seen: bool


class FeedResponse(BaseModel):
    """Response body for GET /feed."""

    items: list[FeedItemResponse]
    next_cursor: str | None
