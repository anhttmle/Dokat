"""Report service — persist user reports for moderation.

A report stores a fixed-enum reason (DL-F10-06) for the
Admin/Moderation team. It never auto-blocks or hides the reported user
(AC-F10-5) and the same pair may be reported multiple times (no UNIQUE).
Self-reports and out-of-enum reasons are rejected (DL-F10-11).

Refs: Design §1.4, §4.1; FR-6, FR-7; AC-F10-5; DL-F10-06, DL-F10-11
"""

import uuid

from sqlalchemy.orm import Session

from app.models.report import Report, ReportReason


class SelfReportError(Exception):
    """Raised when a user attempts to report themselves (DL-F10-11)."""


class InvalidReasonError(Exception):
    """Raised when the report reason is outside the enum (DL-F10-06)."""


def report_user(
    db: Session,
    *,
    reporter_id: str,
    reported_user_id: str,
    reason: str,
) -> Report:
    """Insert a report row after validating the reason and actors.

    Args:
        db: Active SQLAlchemy session.
        reporter_id: UUID string of the reporting user.
        reported_user_id: UUID string of the reported user.
        reason: Reason string; must be a ``ReportReason`` value.

    Returns:
        The newly created ``Report`` ORM object.

    Raises:
        SelfReportError: If reporter and reported are the same user.
        InvalidReasonError: If ``reason`` is not a valid enum value
            (DL-F10-06).
    """
    if reporter_id == reported_user_id:
        raise SelfReportError("Cannot report yourself")

    try:
        reason_enum = ReportReason(reason)
    except ValueError as exc:
        raise InvalidReasonError(f"Invalid report reason: {reason!r}") from exc

    report = Report(
        reporter_id=uuid.UUID(reporter_id),
        reported_user_id=uuid.UUID(reported_user_id),
        reason=reason_enum,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
