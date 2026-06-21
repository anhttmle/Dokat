"""Minimal Photo ORM model required by F02 (timeline & link-photo).

The full ``photos`` table schema will be defined in F04/F05.
This stub exposes only the columns consumed by F02 endpoints:
  - ``user_id``  — ownership check in link-photo
  - ``pet_id``   — FK to pet_profiles; nullable; set by link-photo
  - ``cdn_url``  — returned in the timeline response
  - ``taken_at`` — timeline ordering cursor
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.user import Base


class Photo(Base):
    """Feed photo that can optionally be linked to a pet profile.

    A photo belongs to exactly one user and at most one pet
    (``pet_id`` is a nullable FK — DL-F02-03).
    """

    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pet_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cdn_url: Mapped[str] = mapped_column(Text, nullable=False)
    taken_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
