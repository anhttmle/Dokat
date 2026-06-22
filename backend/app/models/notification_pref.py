"""SQLAlchemy ORM model for notification_preferences table (F09).

Opt-out model: absence of a row means the preference is enabled.
Rows only exist when the user has changed a preference from the
default (DL-F09-06).

Refs: Design §2.2, §2.4; AC-F09-4, AC-F09-5; DL-F09-06
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.user import Base


class ReminderType(enum.StrEnum):
    """Reminder categories configurable per user."""

    feeding = "feeding"
    sleeping = "sleeping"
    bathing = "bathing"
    playing = "playing"


class NotificationPreference(Base):
    """User-level opt-out row for a single reminder type.

    No row → preference enabled (opt-out model, DL-F09-06).
    ``enabled=False`` → reminder suppressed for this type.
    """

    __tablename__ = "notification_preferences"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "reminder_type",
            name="notif_pref_unique_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reminder_type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType, name="reminder_type", native_enum=False),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
