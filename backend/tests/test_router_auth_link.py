"""Tests for POST /auth/link endpoint.

Written TDD-style; all 5 tests expected to FAIL (RED) until task 5.2
is complete.

Refs: FR-7, FR-8, FR-11; AC-F01-5, AC-F01-8
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.user import Base, OAuthProvider, User, UserProvider
from app.routers.auth import get_db

_HEADERS = {"Authorization": "Bearer fake-token"}

_FIREBASE_PROVIDER_MAP = {
    "google": "google.com",
    "apple": "apple.com",
    "facebook": "facebook.com",
}


def _make_token(
    uid: str,
    provider: str | None = None,
    provider_uid: str | None = None,
) -> dict:
    """Build a decoded Firebase ID Token dict for mocking.

    When *provider* is None, returns an anonymous token with no
    identities.  Otherwise, sets ``sign_in_provider`` and
    ``identities`` to match the given provider/uid pair.

    Args:
        uid: The Firebase user ID.
        provider: Short provider name: "google", "apple", "facebook".
        provider_uid: Provider-specific subject string.

    Returns:
        Dict that mimics ``firebase_admin.auth.verify_id_token`` output.
    """
    if provider is None:
        return {
            "uid": uid,
            "firebase": {
                "sign_in_provider": "anonymous",
                "identities": {},
            },
        }

    firebase_provider = _FIREBASE_PROVIDER_MAP[provider]
    return {
        "uid": uid,
        "firebase": {
            "sign_in_provider": firebase_provider,
            "identities": {firebase_provider: [provider_uid]},
        },
    }


@pytest.fixture()
def db_session() -> Session:
    """Isolated SQLite in-memory session per test.

    ``StaticPool`` forces SQLAlchemy to reuse a single connection so
    the in-memory database is visible across all threads.
    ``check_same_thread=False`` lets FastAPI's worker thread reuse
    that connection (DL-014).
    """
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


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """TestClient with the DB dependency overridden per test."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _seed_user(
    db: Session,
    firebase_uid: str,
    anonymous: bool = True,
) -> User:
    """Insert a minimal User row and return it."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid=firebase_uid,
        is_anonymous=anonymous,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_link_single_provider(client: TestClient, db_session: Session) -> None:
    """Token with google provider → user_providers created.

    After a successful link:
    - HTTP 200
    - ``is_anonymous`` is False
    - ``providers`` == ["google"]
    - ``merged`` is False
    - Exactly 1 UserProvider row in DB
    """
    _seed_user(db_session, "user-single-link")

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = _make_token(
            "user-single-link", "google", "google-sub-001"
        )
        response = client.post("/auth/link", headers=_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["is_anonymous"] is False
    assert body["providers"] == ["google"]
    assert body.get("merged") is False

    user = (
        db_session.query(User).filter_by(firebase_uid="user-single-link").one()
    )
    assert user.is_anonymous is False
    assert db_session.query(UserProvider).count() == 1


def test_link_multiple_providers(
    client: TestClient, db_session: Session
) -> None:
    """Link apple then google → providers=['apple','google'], no dup.

    Two separate calls with different providers on the same user must
    produce exactly 2 UserProvider rows and both provider names in
    the response.
    """
    _seed_user(db_session, "user-multi-link")

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = _make_token(
            "user-multi-link", "apple", "apple-sub-001"
        )
        client.post("/auth/link", headers=_HEADERS)

        mock.return_value = _make_token(
            "user-multi-link", "google", "google-sub-001"
        )
        response = client.post("/auth/link", headers=_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["providers"]) == ["apple", "google"]
    assert db_session.query(UserProvider).count() == 2


def test_link_idempotent(client: TestClient, db_session: Session) -> None:
    """Same provider linked twice → no duplicate row, returns 200.

    The second call must not create a second UserProvider row and
    must still return HTTP 200.
    """
    _seed_user(db_session, "user-idempotent")

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = _make_token(
            "user-idempotent", "google", "google-sub-002"
        )
        client.post("/auth/link", headers=_HEADERS)
        response = client.post("/auth/link", headers=_HEADERS)

    assert response.status_code == 200
    assert db_session.query(UserProvider).count() == 1


def test_link_merge_existing_account(
    client: TestClient, db_session: Session
) -> None:
    """Provider owned by user B → merged=True, user_id = user_B.id.

    When the guest user calls /auth/link with a (provider, provider_uid)
    that already belongs to user B:
    - Response: HTTP 200, merged=True, user_id == user_B.id
    - Guest user record is deleted from DB
    """
    user_b = _seed_user(db_session, "user-b-uid", anonymous=False)
    db_session.add(
        UserProvider(
            user_id=user_b.id,
            provider=OAuthProvider.google,
            provider_uid="google-sub-shared",
        )
    )
    db_session.commit()

    _seed_user(db_session, "guest-uid")

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = _make_token(
            "guest-uid", "google", "google-sub-shared"
        )
        response = client.post("/auth/link", headers=_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["merged"] is True
    assert body["user_id"] == str(user_b.id)

    assert (
        db_session.query(User).filter_by(firebase_uid="guest-uid").count() == 0
    )


def test_link_token_without_provider_returns_422(
    client: TestClient, db_session: Session
) -> None:
    """Anonymous token (no provider) → HTTP 422, AUTH_PROVIDER_NOT_FOUND.

    A token with ``sign_in_provider == "anonymous"`` carries no OAuth
    identity and must be rejected before any DB write occurs.
    """
    _seed_user(db_session, "user-no-provider")

    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = _make_token("user-no-provider")
        response = client.post("/auth/link", headers=_HEADERS)

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "AUTH_PROVIDER_NOT_FOUND"
