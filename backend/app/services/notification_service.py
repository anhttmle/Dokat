"""Notification service — send FCM push notifications (best-effort).

Notifications are fire-and-forget: if FCM fails, we log a warning and
continue.  Friendship creation is never rolled back due to notification
failure (Design §1.2, §5.1).

Refs: Design §1.2
"""

import logging

logger = logging.getLogger(__name__)


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
