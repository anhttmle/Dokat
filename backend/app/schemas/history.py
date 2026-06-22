"""Pydantic schemas for the history endpoints (F08).

``SentHistoryItemResponse`` and ``ReceivedHistoryItemResponse`` mirror
the client types (Design §2.1). Each response wraps the page plus an
opaque ``next_cursor`` reused from the feed cursor (DL-F08-04).

Refs: Design §2.1, §3.1, §3.2, §4.1
"""

from pydantic import BaseModel


class SentHistoryItemResponse(BaseModel):
    """A single photo the viewer sent within the last 24h."""

    post_id: str
    cdn_url: str
    created_at: str
    recipient_count: int
    seen_count: int


class ReceivedHistoryItemResponse(BaseModel):
    """A single photo the viewer received within the last 24h."""

    post_id: str
    sender_id: str
    sender_display_name: str | None
    sender_avatar_url: str | None
    pet_name: str | None
    cdn_url: str
    created_at: str
    seen: bool


class SentHistoryResponse(BaseModel):
    """Response body for GET /history/sent."""

    items: list[SentHistoryItemResponse]
    next_cursor: str | None


class ReceivedHistoryResponse(BaseModel):
    """Response body for GET /history/received."""

    items: list[ReceivedHistoryItemResponse]
    next_cursor: str | None
