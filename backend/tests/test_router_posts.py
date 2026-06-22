"""API-level tests for the posts router (/posts).

Mocks the service / storage layers (mirrors test_router_friends.py and
test_router_profile.py). Uses SQLite in-memory for the resolved-user
lookup and ``moto`` for the presigned-URL happy path.

Refs: Design §3.1, §3.2, §6.3; FR-4, FR-5;
AC-F05-4; DL-F05-02, DL-F05-07; F11 §3.1, AC-F11-3
"""

import types
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.post  # noqa: F401  register table on Base
import app.models.post_recipient  # noqa: F401  register table on Base
from app.main import app
from app.models.user import Base, User
from app.routers.auth import get_db
from app.services.post_service import InvalidRecipientError

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
def client(db_session: Session, mock_verify_id_token) -> TestClient:
    """TestClient with DB overridden and Firebase token mocked."""
    now = datetime.now(UTC)
    db_session.add(
        User(
            firebase_uid="test-uid-anonymous",
            is_anonymous=False,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _fake_post() -> types.SimpleNamespace:
    """Return a post-like object with the fields the router reads."""
    created = datetime(2026, 6, 22, 0, 43, tzinfo=UTC)
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        expires_at=datetime(2026, 6, 23, 0, 43, tzinfo=UTC),
        created_at=created,
    )


def test_upload_url_returns_presigned(client: TestClient) -> None:
    """200 with upload_url/object_key/cdn_url under the posts/ prefix."""
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(
            Bucket="pawsnap"
        )
        resp = client.post(
            "/posts/upload-url",
            headers=_HEADERS,
            json={"content_type": "image/jpeg"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "upload_url" in body
    assert "cdn_url" in body
    assert body["object_key"].startswith("posts/")


def test_upload_url_invalid_content_type(client: TestClient) -> None:
    """Unsupported content_type returns 400 INVALID_CONTENT_TYPE."""
    resp = client.post(
        "/posts/upload-url",
        headers=_HEADERS,
        json={"content_type": "video/mp4"},
    )

    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_CONTENT_TYPE"


def test_create_post_201(client: TestClient) -> None:
    """201 with all response fields present."""
    with patch(
        "app.routers.posts.post_service.create_post",
        return_value=(_fake_post(), 2),
    ):
        resp = client.post(
            "/posts",
            headers=_HEADERS,
            json={
                "s3_key": "posts/u/1.jpg",
                "cdn_url": "https://cdn/u/1.jpg",
                "recipient_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert {"post_id", "expires_at", "recipient_count", "created_at"} <= set(
        body
    )
    assert body["recipient_count"] == 2


def test_create_post_no_latlng_in_response(client: TestClient) -> None:
    """Response must not expose latitude/longitude (F11 AC-F11-3)."""
    with patch(
        "app.routers.posts.post_service.create_post",
        return_value=(_fake_post(), 0),
    ):
        resp = client.post(
            "/posts",
            headers=_HEADERS,
            json={
                "s3_key": "posts/u/1.jpg",
                "cdn_url": "https://cdn/u/1.jpg",
                "recipient_ids": [],
                "latitude": 10.77621500,
                "longitude": 106.69505800,
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert "latitude" not in body
    assert "longitude" not in body


def test_create_post_zero_recipients_201(client: TestClient) -> None:
    """0 recipients still returns 201 with recipient_count = 0."""
    with patch(
        "app.routers.posts.post_service.create_post",
        return_value=(_fake_post(), 0),
    ):
        resp = client.post(
            "/posts",
            headers=_HEADERS,
            json={
                "s3_key": "posts/u/1.jpg",
                "cdn_url": "https://cdn/u/1.jpg",
                "recipient_ids": [],
            },
        )

    assert resp.status_code == 201
    assert resp.json()["recipient_count"] == 0


def test_create_post_bad_latlng_422(client: TestClient) -> None:
    """Out-of-range coordinates fail Pydantic validation (F11 §3.1)."""
    resp = client.post(
        "/posts",
        headers=_HEADERS,
        json={
            "s3_key": "posts/u/1.jpg",
            "cdn_url": "https://cdn/u/1.jpg",
            "recipient_ids": [],
            "latitude": 91,
            "longitude": 181,
        },
    )

    assert resp.status_code == 422


def test_create_post_non_friend_422(client: TestClient) -> None:
    """A non-friend recipient returns 422 INVALID_RECIPIENT."""
    with patch(
        "app.routers.posts.post_service.create_post",
        side_effect=InvalidRecipientError(),
    ):
        resp = client.post(
            "/posts",
            headers=_HEADERS,
            json={
                "s3_key": "posts/u/1.jpg",
                "cdn_url": "https://cdn/u/1.jpg",
                "recipient_ids": [str(uuid.uuid4())],
            },
        )

    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INVALID_RECIPIENT"
