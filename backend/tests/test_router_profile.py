"""Tests for the owner profile router (/profile/me).

Written TDD-style; tests are expected to FAIL until the profile
service is implemented in task 3.2.

Refs: AC-F02-1, AC-F02-2; Design §3.1, §3.2
"""

from datetime import UTC, datetime
from unittest.mock import patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.pet_profile  # noqa: F401  (register table on Base)
from app.main import app
from app.models.user import Base, User
from app.routers.auth import get_db

_HEADERS = {"Authorization": "Bearer fake-token"}


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


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    """TestClient with the DB dependency overridden per test."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _make_user(
    db_session: Session,
    *,
    firebase_uid: str = "owner-uid",
    display_name: str | None = "Nguyen Van A",
    avatar_url: str | None = None,
    is_anonymous: bool = False,
) -> User:
    """Insert and return a user row."""
    now = datetime.now(UTC)
    user = User(
        firebase_uid=firebase_uid,
        is_anonymous=is_anonymous,
        display_name=display_name,
        avatar_url=avatar_url,
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_get_owner_profile_returns_display_name(
    client: TestClient, db_session: Session
) -> None:
    """GET /profile/me returns display_name and avatar_url from users."""
    _make_user(
        db_session,
        display_name="Nguyen Van A",
        avatar_url="https://cdn.pawsnap.app/avatars/users/a.jpg",
    )
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "owner-uid"}
        response = client.get("/profile/me", headers=_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Nguyen Van A"
    assert body["avatar_url"] == (
        "https://cdn.pawsnap.app/avatars/users/a.jpg"
    )
    assert body["is_anonymous"] is False


def test_get_owner_profile_anonymous_user(
    client: TestClient, db_session: Session
) -> None:
    """GET /profile/me with anonymous user returns 200, display_name=None."""
    _make_user(
        db_session,
        display_name=None,
        is_anonymous=True,
    )
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "owner-uid"}
        response = client.get("/profile/me", headers=_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] is None
    assert body["is_anonymous"] is True


def test_patch_display_name_updates_db(
    client: TestClient, db_session: Session
) -> None:
    """PATCH /profile/me {display_name: "New"} → 200, DB updated."""
    _make_user(db_session, display_name="Old Name")
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "owner-uid"}
        response = client.patch(
            "/profile/me",
            headers=_HEADERS,
            json={"display_name": "New Name"},
        )

    assert response.status_code == 200
    assert response.json()["display_name"] == "New Name"
    db_session.expire_all()
    user = (
        db_session.query(User).filter(User.firebase_uid == "owner-uid").one()
    )
    assert user.display_name == "New Name"


def test_patch_avatar_url(client: TestClient, db_session: Session) -> None:
    """PATCH /profile/me with avatar_url updates the DB."""
    _make_user(db_session, avatar_url=None)
    new_url = "https://cdn.pawsnap.app/avatars/users/new.jpg"
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "owner-uid"}
        response = client.patch(
            "/profile/me",
            headers=_HEADERS,
            json={"avatar_url": new_url},
        )

    assert response.status_code == 200
    assert response.json()["avatar_url"] == new_url


def test_patch_owner_profile_partial_update(
    client: TestClient, db_session: Session
) -> None:
    """Sending only display_name leaves avatar_url unchanged in DB."""
    _make_user(
        db_session,
        display_name="Keep Avatar",
        avatar_url="https://cdn.pawsnap.app/avatars/users/keep.jpg",
    )
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "owner-uid"}
        response = client.patch(
            "/profile/me",
            headers=_HEADERS,
            json={"display_name": "Changed"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Changed"
    assert body["avatar_url"] == (
        "https://cdn.pawsnap.app/avatars/users/keep.jpg"
    )


def test_oauth_autofill_sets_display_name_when_null(
    client: TestClient, db_session: Session
) -> None:
    """After POST /auth/link, display_name is filled from Firebase token.

    Simulates the OAuth link flow when user.display_name is NULL:
    the token carries the provider's display name, and autofill_from_oauth
    should persist it only because the column was NULL.
    """
    _make_user(
        db_session,
        firebase_uid="anon-uid",
        display_name=None,
        is_anonymous=True,
    )
    token_with_name = {
        "uid": "anon-uid",
        "name": "Google User",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
        "firebase": {
            "sign_in_provider": "google.com",
            "identities": {"google.com": ["google-sub-autofill"]},
        },
    }
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = token_with_name
        client.post("/auth/link", headers=_HEADERS)

    db_session.expire_all()
    user = db_session.query(User).filter(User.firebase_uid == "anon-uid").one()
    assert user.display_name == "Google User"
    assert user.avatar_url == ("https://lh3.googleusercontent.com/photo.jpg")


def test_presigned_url_owner_avatar(
    client: TestClient, db_session: Session
) -> None:
    """POST /profile/me/avatar/upload-url returns a valid S3 URL."""
    _make_user(db_session)
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(
            Bucket="pawsnap"
        )
        with patch("firebase_admin.auth.verify_id_token") as mock:
            mock.return_value = {"uid": "owner-uid"}
            response = client.post(
                "/profile/me/avatar/upload-url",
                headers=_HEADERS,
                json={"content_type": "image/jpeg"},
            )

    assert response.status_code == 200
    body = response.json()
    assert "upload_url" in body
    assert "cdn_url" in body
    assert body["expires_in"] == 300


def test_presigned_url_invalid_type(
    client: TestClient, db_session: Session
) -> None:
    """Unsupported content_type returns 400 INVALID_CONTENT_TYPE."""
    _make_user(db_session)
    with patch("firebase_admin.auth.verify_id_token") as mock:
        mock.return_value = {"uid": "owner-uid"}
        response = client.post(
            "/profile/me/avatar/upload-url",
            headers=_HEADERS,
            json={"content_type": "video/mp4"},
        )

    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_CONTENT_TYPE"
