"""APScheduler-based reminder job for daily pet reminders (F09).

Architecture (Design §1.2):
- A single ``BackgroundScheduler`` job fires every 1 minute.
- Each run loads ``reminders.yaml`` (cached in memory after first load).
- For each YAML entry, query users with a matching pet species +
  non-null ``fcm_token`` + non-null ``timezone``.
- Convert UTC now → user-local time; fire ``send_reminder`` when
  ``local_hour == entry.hour AND local_minute == entry.minute``.
- Respects the opt-out model: check ``notification_pref_service``
  before sending (AC-F09-5).

Refs: Design §1.2, §2.3, §4.1; AC-F09-3, AC-F09-5, AC-F09-6;
DL-F09-05
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from app.models.notification_pref import ReminderType
from app.models.pet_profile import PetProfile, PetSpecies
from app.models.user import User

logger = logging.getLogger(__name__)

_REMINDERS_CACHE: list["ReminderEntry"] | None = None

DEFAULT_YAML_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "config",
    "reminders.yaml",
)


@dataclass(frozen=True)
class ReminderEntry:
    """A single scheduled reminder slot from the YAML config."""

    species: str
    reminder_type: ReminderType
    hour: int
    minute: int


def load_reminders(yaml_path: str) -> list[ReminderEntry]:
    """Parse ``reminders.yaml`` and return a list of ``ReminderEntry``.

    Args:
        yaml_path: Absolute or relative path to the YAML config file.

    Returns:
        List of validated ``ReminderEntry`` objects.

    Raises:
        ValueError: If ``type`` is not a valid ``ReminderType``.
        FileNotFoundError: If the YAML file does not exist.
    """
    with open(yaml_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    entries: list[ReminderEntry] = []
    for species, slots in (data.get("reminders") or {}).items():
        for slot in slots:
            raw_type = slot["type"]
            try:
                r_type = ReminderType(raw_type)
            except ValueError:
                raise ValueError(
                    f"Invalid reminder type '{raw_type}' in {yaml_path}"
                )
            entries.append(
                ReminderEntry(
                    species=species,
                    reminder_type=r_type,
                    hour=int(slot["hour"]),
                    minute=int(slot["minute"]),
                )
            )
    return entries


def run_reminder_job(
    db_factory: Callable,
    reminders: list[ReminderEntry],
    now_utc: datetime | None = None,
) -> None:
    """Execute a single reminder scan tick.

    Args:
        db_factory: Zero-argument callable returning a SQLAlchemy
            ``Session`` (typically ``SessionLocal``).
        reminders: Pre-loaded list of ``ReminderEntry`` from YAML.
        now_utc: Override current UTC time (used in tests only).
    """
    from app.services import notification_pref_service
    from app.services.notification_service import NotificationService

    utc_now = now_utc or datetime.now(UTC)

    for entry in reminders:
        db = db_factory()
        try:
            _process_entry(db, entry, utc_now)
        except Exception:
            logger.error(
                "Reminder job failed for entry %s", entry, exc_info=True
            )
        finally:
            db.close()


def _process_entry(db, entry: ReminderEntry, utc_now: datetime) -> None:
    """Send reminders for a single YAML entry to matching users."""
    from app.services import notification_pref_service
    from app.services.notification_service import NotificationService

    try:
        species_enum = PetSpecies(entry.species)
    except ValueError:
        logger.warning("Unknown species '%s' in reminders.yaml", entry.species)
        return

    rows = (
        db.query(User, PetProfile)
        .join(PetProfile, PetProfile.user_id == User.id)
        .filter(
            PetProfile.species == species_enum,
            User.fcm_token.isnot(None),
            User.timezone.isnot(None),
        )
        .all()
    )

    for user, pet in rows:
        try:
            tz = ZoneInfo(user.timezone)
        except (ZoneInfoNotFoundError, Exception):
            logger.debug(
                "Skipping user %s: invalid timezone %s",
                user.id,
                user.timezone,
            )
            continue

        local_now = utc_now.astimezone(tz)
        if (
            local_now.hour != entry.hour
            or local_now.minute != entry.minute
        ):
            continue

        prefs = notification_pref_service.get_preferences(db, user.id)
        if not prefs.get(entry.reminder_type, True):
            continue

        svc = NotificationService(db)
        svc.send_reminder(user, pet.name, entry.reminder_type)


def start(app) -> None:
    """Register the reminder job with FastAPI startup/shutdown events.

    Args:
        app: FastAPI application instance.
    """
    from apscheduler.schedulers.background import BackgroundScheduler

    from app.routers.auth import _get_session_factory

    reminders = load_reminders(DEFAULT_YAML_PATH)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_reminder_job,
        trigger="interval",
        minutes=1,
        kwargs={
            "db_factory": _get_session_factory(),
            "reminders": reminders,
        },
        id="reminder_job",
        replace_existing=True,
    )

    @app.on_event("startup")
    def startup() -> None:
        scheduler.start()
        logger.info("Reminder scheduler started.")

    @app.on_event("shutdown")
    def shutdown() -> None:
        scheduler.shutdown(wait=False)
        logger.info("Reminder scheduler stopped.")
