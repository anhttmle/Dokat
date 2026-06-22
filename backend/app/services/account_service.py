"""Account service — unlink OAuth providers / clear device token.

Unlinking guards against removing the user's last provider to avoid
account lock-out (FR-3, AC-F10-2): the backend only syncs the
``user_providers`` row; the Firebase-side unlink is done by the client
(DL-F10-02). Logout clears ``users.fcm_token`` so no push reaches the
signed-out device (DL-F10-07).

Refs: Design §1.1, §1.5, §4.1; FR-3, FR-9; AC-F10-2, AC-F10-6;
DL-F10-02, DL-F10-07
"""

import uuid

from sqlalchemy.orm import Session

from app.models.user import OAuthProvider, User, UserProvider


class LastProviderError(Exception):
    """Raised when unlinking would remove the only provider (AC-F10-2)."""


class ProviderNotLinkedError(Exception):
    """Raised when the provider to unlink is not linked to the user."""


def unlink_provider(db: Session, *, user_id: str, provider: str) -> None:
    """Remove the ``user_providers`` row for the given provider.

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID string of the requesting user.
        provider: Provider name (``apple`` | ``google`` | ``facebook``).

    Raises:
        ProviderNotLinkedError: If the provider is not linked.
        LastProviderError: If it is the user's only linked provider
            (DL-F10-02).
    """
    uid = uuid.UUID(user_id)
    provider_enum = OAuthProvider(provider)

    rows = db.query(UserProvider).filter(UserProvider.user_id == uid).all()
    target = next((r for r in rows if r.provider == provider_enum), None)
    if target is None:
        raise ProviderNotLinkedError(f"Provider {provider!r} not linked")

    if len(rows) <= 1:
        raise LastProviderError("Cannot unlink the last provider")

    db.delete(target)
    db.commit()


def clear_device_token(db: Session, user_id: str) -> None:
    """Clear the user's FCM token (idempotent — DL-F10-07).

    Args:
        db: Active SQLAlchemy session.
        user_id: UUID string of the requesting user.
    """
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if user is not None and user.fcm_token is not None:
        user.fcm_token = None
        db.commit()
