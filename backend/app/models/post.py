"""SQLAlchemy ORM model for the posts table (F05).

A post is a single sent photo owned by one user. It always carries an
``expires_at`` (created_at + 24h — DL-F05-03) and may optionally store
the capture coordinates supplied by F11 (``latitude``/``longitude``).
The recipient set lives in ``post_recipients`` (may be empty — FR-7).

Refs: Design §2.1; DL-F05-01, DL-F05-03; F11 Design §2.3
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.user import Base


class Post(Base):
    """A sent photo (broadcast post) created by a single user."""

    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    cdn_url: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(11, 8), nullable=True
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 8), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
