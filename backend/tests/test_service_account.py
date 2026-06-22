"""Unit tests for account_service — unlink provider / clear device token.

Unlinking guards against removing the last provider to avoid account
lock-out (FR-3, AC-F10-2, DL-F10-02). Logout clears the FCM token so no
push reaches the signed-out device (DL-F10-07).

Refs: Design §1.1, §1.5, §6.3; FR-3, FR-9; AC-F10-2, AC-F10-6;
DL-F10-02, DL-F10-07
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.user import Base, OAuthProvider, User, UserProvider
from app.services.account_service import (
    LastProviderError,
    ProviderNotLinkedError,
    clear_device_token,
    unlink_provider,
)


@pytest.fixture()
def db_session() -> Session:
    """Isolated SQLite in-memory session per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=True)
    session = factory()
    yield session
    session.close()
    engine.dispose()


def _make_user(db: Session, *, fcm_token: str | None = None) -> User:
    """Insert and return a minimal User row."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid="uid-account",
        is_anonymous=False,
        fcm_token=fcm_token,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _link(db: Session, user: User, provider: OAuthProvider) -> None:
    """Attach an OAuth provider row to *user*."""
    db.add(
        UserProvider(
            user_id=user.id,
            provider=provider,
            provider_uid=f"{provider.value}-sub-{user.id}",
        )
    )
    db.commit()


def test_unlink_removes_provider(db_session: Session) -> None:
    """With ≥2 providers, unlink removes exactly one row (FR-3)."""
    user = _make_user(db_session)
    _link(db_session, user, OAuthProvider.google)
    _link(db_session, user, OAuthProvider.apple)

    unlink_provider(db_session, user_id=str(user.id), provider="google")

    remaining = (
        db_session.query(UserProvider)
        .filter(UserProvider.user_id == user.id)
        .all()
    )
    assert {p.provider for p in remaining} == {OAuthProvider.apple}


def test_unlink_last_provider_raises(db_session: Session) -> None:
    """Unlinking the only provider raises LastProviderError (AC-F10-2)."""
    user = _make_user(db_session)
    _link(db_session, user, OAuthProvider.apple)

    with pytest.raises(LastProviderError):
        unlink_provider(db_session, user_id=str(user.id), provider="apple")

    # Row must remain intact.
    assert (
        db_session.query(UserProvider)
        .filter(UserProvider.user_id == user.id)
        .count()
        == 1
    )


def test_unlink_not_linked_raises(db_session: Session) -> None:
    """Unlinking a provider that is not linked raises an error."""
    user = _make_user(db_session)
    _link(db_session, user, OAuthProvider.google)
    _link(db_session, user, OAuthProvider.apple)

    with pytest.raises(ProviderNotLinkedError):
        unlink_provider(db_session, user_id=str(user.id), provider="facebook")


def test_clear_device_token(db_session: Session) -> None:
    """Logout clears the user's fcm_token (DL-F10-07)."""
    user = _make_user(db_session, fcm_token="device-token-123")

    clear_device_token(db_session, str(user.id))

    db_session.refresh(user)
    assert user.fcm_token is None


def test_clear_device_token_idempotent(db_session: Session) -> None:
    """Clearing an already-null token is a no-op (DL-F10-07)."""
    user = _make_user(db_session, fcm_token=None)

    clear_device_token(db_session, str(user.id))

    db_session.refresh(user)
    assert user.fcm_token is None
