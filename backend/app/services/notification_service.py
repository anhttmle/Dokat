"""Notification service — send FCM push notifications (best-effort).

Notifications are fire-and-forget: if FCM fails, we log a warning and
continue.  Friendship creation is never rolled back due to notification
failure (Design §1.2, §5.1).

Refs: Design §1.2
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Send FCM push notifications (best-effort, no raise on failure).

    Args:
        db: Active SQLAlchemy session used to read user FCM tokens.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def send_new_friend(
        self,
        initiator_id: str,
        scanner_name: str | None,
    ) -> None:
        """Send a 'new friend' FCM push to the Initiator.

        Reads ``fcm_token`` from the database for the given initiator.
        No-ops if the token is absent. Logs a warning on any error;
        never raises (best-effort delivery per Design §5.1).

        Args:
            initiator_id: UUID string of the QR owner (notification
                recipient).
            scanner_name: Display name of the Scanner shown in the
                notification body. Falls back to "Someone" if ``None``.
        """
        uid = uuid.UUID(initiator_id)
        user = self._db.query(User).filter(User.id == uid).first()
        if user is None or not user.fcm_token:
            logger.debug(
                "Skipping FCM: no token registered for initiator %s",
                initiator_id,
            )
            return

        name = scanner_name or "Someone"
        try:
            # TODO(F03): replace stub with real Firebase Admin SDK call:
            # message = firebase_admin.messaging.Message(
            #     notification=firebase_admin.messaging.Notification(
            #         title="Bạn bè mới",
            #         body=f"{name} đã kết bạn với bạn",
            #     ),
            #     token=user.fcm_token,
            # )
            # firebase_admin.messaging.send(message)
            logger.info(
                "FCM notification queued for initiator=%s: '%s added you'",
                str(initiator_id)[:8],
                name,
            )
        except Exception:
            logger.warning(
                "FCM send failed for initiator=%s",
                initiator_id,
                exc_info=True,
            )


def send_friend_notification(
    initiator_fcm_token: str | None,
    scanner_display_name: str | None,
) -> None:
    """Send a "new friend" FCM push to the Initiator.

    No-ops silently if *initiator_fcm_token* is ``None`` (user has not
    registered a device token yet).

    Args:
        initiator_fcm_token: FCM device token of the Initiator.
        scanner_display_name: Display name of the Scanner to show in
            the notification body.  Falls back to "Someone" if ``None``.
    """
    if not initiator_fcm_token:
        logger.debug(
            "Skipping FCM: Initiator has no fcm_token registered"
        )
        return

    name = scanner_display_name or "Someone"
    logger.info(
        "FCM notification queued for token=%r: '%s added you as a friend'",
        initiator_fcm_token[:8] + "...",
        name,
    )
    # TODO(F03-task-notification): implement real Firebase Admin SDK call
    # firebase_admin.messaging.send(...)
