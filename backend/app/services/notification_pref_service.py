"""Notification preference service — get / set per-user reminder prefs.

Opt-out model: absence of a row means ``enabled=True``.
Upsert is idempotent (INSERT … ON CONFLICT DO UPDATE).

Refs: Design §3.2, §3.3; AC-F09-4, AC-F09-5; DL-F09-06
"""

import uuid

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.notification_pref import (
    NotificationPreference,
    ReminderType,
)


def get_preferences(
    db: Session, user_id: uuid.UUID
) -> dict[ReminderType, bool]:
    """Return all four reminder preferences for a user.

    Missing rows default to ``True`` (opt-out model, DL-F09-06).

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID of the requesting user.

    Returns:
        Dict mapping each ``ReminderType`` to its enabled state.
    """
    rows = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .all()
    )
    stored = {row.reminder_type: row.enabled for row in rows}
    return {rt: stored.get(rt, True) for rt in ReminderType}


def set_preference(
    db: Session,
    user_id: uuid.UUID,
    reminder_type: ReminderType,
    enabled: bool,
) -> None:
    """Upsert a single reminder preference for a user.

    Idempotent: calling with the same value twice produces no error
    and leaves the row in the expected state.

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID of the user.
        reminder_type: Which reminder to toggle.
        enabled: New enabled state.
    """
    stmt = (
        sqlite_insert(NotificationPreference)
        .values(
            id=uuid.uuid4(),
            user_id=user_id,
            reminder_type=reminder_type,
            enabled=enabled,
        )
        .on_conflict_do_update(
            index_elements=["user_id", "reminder_type"],
            set_={"enabled": enabled},
        )
    )
    db.execute(stmt)
    db.commit()
