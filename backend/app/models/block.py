"""SQLAlchemy ORM model for the blocked_users table (F10).

A block is recorded one-directionally (``blocker_id`` → ``blocked_id``)
but takes effect both ways in the feed (DL-F10-04). Blocking also
deletes the friendship (DL-F10-03), so the blocked user disappears from
the friend list as a side effect (DL-F10-10).

``CHECK (blocker_id <> blocked_id)`` is omitted because SQLite does not
honour it the same way as PostgreSQL; the service layer rejects
self-blocks instead (DL-F10-11).

Refs: Design §2.1, §2.3; FR-4; DL-F10-03, DL-F10-04, DL-F10-11
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.user import Base


class BlockedUser(Base):
    """A single block edge (blocker → blocked)."""

    __tablename__ = "blocked_users"

    __table_args__ = (
        UniqueConstraint(
            "blocker_id", "blocked_id", name="blocked_users_unique_pair"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    blocker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    blocked_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
