"""SQLAlchemy ORM model for the post_recipients table (F05).

Links a post to each chosen recipient (many-to-many). The table may be
empty for a post (0 recipients — FR-6, AC-F05-4). ``seen_at`` is created
here as its natural home but its write logic belongs to F07 (DL-F05-04).

Refs: Design §2.2; FR-6; AC-F05-4; DL-F05-04
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.user import Base


class PostRecipient(Base):
    """A single recipient edge for a post (post ↔ user)."""

    __tablename__ = "post_recipients"

    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "recipient_id",
            name="post_recipients_unique_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
