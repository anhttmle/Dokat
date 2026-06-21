"""SQLAlchemy ORM model for the friendships table."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.user import Base


class Friendship(Base):
    """Represents a bidirectional friendship edge between two users.

    Canonical ordering: ``user_id_a < user_id_b`` (UUID string
    comparison) is enforced at the service layer before every
    insert/lookup.  A DB-level UNIQUE constraint prevents duplicates.

    ``CHECK (user_id_a < user_id_b)`` is omitted here because SQLite
    does not honour it the same way as PostgreSQL; the service layer
    enforces canonical order instead (DL-F03-01).
    """

    __tablename__ = "friendships"

    __table_args__ = (
        UniqueConstraint("user_id_a", "user_id_b", name="friendships_unique_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id_a: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id_b: Mapped[uuid.UUID] = mapped_column(
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
