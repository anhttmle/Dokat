"""Pydantic schemas for the seen endpoints (F07).

Mirrors the client types in Design §2.1: ``SeenViewerResponse`` is a
single viewer, ``SeenByResponse`` wraps the aggregate count plus the
viewer list, and ``SeenResponse`` acknowledges a mark-seen call.

Refs: Design §2.1, §3.1, §3.2, §4.1
"""

from pydantic import BaseModel


class SeenResponse(BaseModel):
    """Response body for POST /posts/{id}/seen."""

    post_id: str
    seen_at: str


class SeenViewerResponse(BaseModel):
    """A single recipient who has seen the post (for the sender)."""

    user_id: str
    display_name: str | None
    avatar_url: str | None
    seen_at: str


class SeenByResponse(BaseModel):
    """Response body for GET /posts/{id}/seen-by."""

    post_id: str
    seen_count: int
    viewers: list[SeenViewerResponse]
