"""Pydantic schemas for notification preferences endpoints (F09).

Refs: Design §3.2, §3.3; AC-F09-4, AC-F09-5
"""

from pydantic import BaseModel

from app.models.notification_pref import ReminderType


class SetPreferenceRequest(BaseModel):
    """Request body for PUT /notifications/preferences/{reminder_type}."""

    enabled: bool


class PreferencesResponse(BaseModel):
    """Response body for GET /notifications/preferences.

    All four reminder types are always present (DL-F09-06).
    Absent rows default to ``true`` (opt-out model).
    """

    feeding: bool
    sleeping: bool
    bathing: bool
    playing: bool

    @classmethod
    def from_dict(
        cls, prefs: dict[ReminderType, bool]
    ) -> "PreferencesResponse":
        """Build response from a preferences dict."""
        return cls(
            feeding=prefs.get(ReminderType.feeding, True),
            sleeping=prefs.get(ReminderType.sleeping, True),
            bathing=prefs.get(ReminderType.bathing, True),
            playing=prefs.get(ReminderType.playing, True),
        )
