"""SQLAlchemy ORM model for the reports table (F10).

A report records that one user flagged another with a fixed reason
(``report_reason`` enum — DL-F10-06). Reports are stored for the
Admin/Moderation team and never auto-hide or block the reported user
(AC-F10-5). Multiple reports for the same pair are allowed (no UNIQUE).

Self-reports are rejected at the service layer (DL-F10-11).

Refs: Design §2.2, §2.3; FR-6, FR-7; DL-F10-06, DL-F10-11
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.user import Base


class ReportReason(enum.StrEnum):
    """Fixed set of reasons a user may report another user."""

    spam = "spam"
    inappropriate = "inappropriate"
    harassment = "harassment"
    other = "other"


class Report(Base):
    """A single user-to-user report record."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reported_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[ReportReason] = mapped_column(
        Enum(ReportReason, name="report_reason", create_constraint=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
