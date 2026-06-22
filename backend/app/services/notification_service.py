"""Notification service — send FCM push notifications (best-effort).

Notifications are fire-and-forget: FCM failures are logged as warnings
and never propagate to callers. Post creation is never rolled back due
to notification failure (DL-F05-05).

New in F09:
- ``send_new_photo``: push to each post recipient after post commit.
- ``send_reminder``: push a daily reminder for a single user.
- ``_is_blocked``: check block relationship before sending (DL-F09-04).

Refs: Design §1.1, §1.2, §4.1, §5; AC-F09-1, AC-F09-2, AC-F09-3;
DL-F05-05, DL-F09-01, DL-F09-04
"""

import logging
import uuid

import firebase_admin.messaging
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.block import BlockedUser
from app.models.notification_pref import ReminderType
from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.models.user import User

logger = logging.getLogger(__name__)

REMINDER_LABELS: dict[ReminderType, str] = {
    ReminderType.feeding: "cho ăn",
    ReminderType.sleeping: "ngủ",
    ReminderType.bathing: "tắm",
    ReminderType.playing: "chơi",
}


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

    def send_new_photo(self, post: Post, db: Session) -> None:
        """Send a 'new photo' push to each post recipient.

        Steps (Design §1.1):
        1. Read recipients from post_recipients for this post.
        2. Skip recipients blocked by the sender (DL-F09-04).
        3. Skip recipients with no fcm_token.
        4. Call FCM with post data (AC-F09-1, AC-F09-2).
        5. All FCM errors are caught + logged; no raise (DL-F05-05).

        Args:
            post: The newly created ``Post`` ORM instance.
            db: Active session (may differ from ``self._db``).
        """
        recipients = (
            db.query(PostRecipient)
            .filter(PostRecipient.post_id == post.id)
            .all()
        )

        sender = db.query(User).filter(User.id == post.user_id).first()
        sender_name = (
            sender.display_name if sender else None
        ) or "Ai đó"

        for recipient_row in recipients:
            rid = recipient_row.recipient_id
            if _is_blocked(post.user_id, rid, db):
                logger.debug(
                    "Skipping FCM: sender %s blocked by/with recipient %s",
                    post.user_id,
                    rid,
                )
                continue

            recipient = db.query(User).filter(User.id == rid).first()
            if recipient is None or not recipient.fcm_token:
                logger.debug(
                    "Skipping FCM: no token for recipient %s", rid
                )
                continue

            _send_fcm(
                token=recipient.fcm_token,
                title=sender_name,
                body="đã gửi ảnh thú cưng mới cho bạn",
                image=post.cdn_url,
                data={
                    "post_id": str(post.id),
                    "screen": "FeedDetail",
                },
            )

    def send_reminder(
        self,
        user: User,
        pet_name: str,
        reminder_type: ReminderType,
    ) -> None:
        """Send a daily reminder push to a single user.

        Best-effort: FCM errors are caught and logged (DL-F09-05).

        Args:
            user: Target user (must have non-null fcm_token).
            pet_name: Name of the user's pet to show in the message.
            reminder_type: Which reminder category.
        """
        if not user.fcm_token:
            logger.debug(
                "Skipping reminder FCM: no token for user %s", user.id
            )
            return

        label = REMINDER_LABELS.get(reminder_type, str(reminder_type))
        body = f"Đến giờ {label} cho {pet_name} rồi!"
        _send_fcm(
            token=user.fcm_token,
            title="Nhắc nhở thú cưng",
            body=body,
        )


def _is_blocked(
    sender_id: uuid.UUID,
    recipient_id: uuid.UUID,
    db: Session,
) -> bool:
    """Return True if a block exists between sender and recipient.

    Checks both directions (sender→recipient and recipient→sender).

    Args:
        sender_id: UUID of the post sender.
        recipient_id: UUID of the recipient.
        db: Active session.
    """
    row = (
        db.query(BlockedUser)
        .filter(
            or_(
                and_(
                    BlockedUser.blocker_id == sender_id,
                    BlockedUser.blocked_id == recipient_id,
                ),
                and_(
                    BlockedUser.blocker_id == recipient_id,
                    BlockedUser.blocked_id == sender_id,
                ),
            )
        )
        .first()
    )
    return row is not None


def _send_fcm(
    *,
    token: str,
    title: str,
    body: str,
    image: str | None = None,
    data: dict[str, str] | None = None,
) -> None:
    """Build and send a Firebase Cloud Messaging message.

    Errors are caught and logged as warnings (best-effort).

    Args:
        token: FCM device token.
        title: Notification title.
        body: Notification body text.
        image: Optional image URL (thumbnail).
        data: Optional data payload dict for deep linking.
    """
    try:
        msg = firebase_admin.messaging.Message(
            notification=firebase_admin.messaging.Notification(
                title=title,
                body=body,
                image=image,
            ),
            data=data or {},
            token=token,
        )
        firebase_admin.messaging.send(msg)
    except Exception:
        logger.warning(
            "FCM send failed for token=%s", token[:8], exc_info=True
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
        logger.debug("Skipping FCM: Initiator has no fcm_token registered")
        return

    name = scanner_display_name or "Someone"
    logger.info(
        "FCM notification queued for token=%r: '%s added you as a friend'",
        initiator_fcm_token[:8] + "...",
        name,
    )
