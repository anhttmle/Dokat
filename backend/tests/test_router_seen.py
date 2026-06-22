"""API-level tests for the seen router (/posts/{id}/seen, seen-by).

Mocks seen_service and uses SQLite in-memory for the resolved-user
lookup (mirrors test_router_feed.py / test_router_posts.py). Firebase
token verification is mocked via the shared ``mock_verify_id_token``
fixture.

Refs: Design §3.1, §3.2, §6.2;
AC-F07-1, AC-F07-2, AC-F07-3;
DL-F07-03, DL-F07-04, DL-F07-09
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.post  # noqa: F401  register table on Base
import app.models.post_recipient  # noqa: F401  register table on Base
from app.main import app
from app.models.user import Base, User
from app.routers.auth import get_db
from app.services.seen_service import (
    NotRecipientError,
    NotSenderError,
    PostNotFoundError,
)

_HEADERS = {"Authorization": "Bearer fake-token"}
_POST_ID = "11111111-1111-1111-1111-111111111111"
_SEEN_AT = "2026-06-22T07:05:00+00:00"


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
    """TestClient with the viewer user seeded and Firebase mocked."""
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


@pytest.fixture()
def empty_client(db_session: Session, mock_verify_id_token) -> TestClient:
    """TestClient with no user row (for USER_NOT_FOUND)."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# --- POST /posts/{id}/seen ---------------------------------------------


def test_mark_seen_200(client: TestClient) -> None:
    """200 with {post_id, seen_at} (AC-F07-1)."""
    with patch(
        "app.routers.seen.seen_service.mark_seen",
        return_value=datetime.fromisoformat(_SEEN_AT),
    ):
        resp = client.post(f"/posts/{_POST_ID}/seen", headers=_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["post_id"] == _POST_ID
    assert "seen_at" in body


def test_mark_seen_idempotent_200(client: TestClient) -> None:
    """Two calls return the same seen_at, both 200 (AC-F07-3)."""
    with patch(
        "app.routers.seen.seen_service.mark_seen",
        return_value=datetime.fromisoformat(_SEEN_AT),
    ):
        first = client.post(f"/posts/{_POST_ID}/seen", headers=_HEADERS)
        second = client.post(f"/posts/{_POST_ID}/seen", headers=_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["seen_at"] == second.json()["seen_at"]


def test_mark_seen_non_recipient_403(client: TestClient) -> None:
    """A non-recipient → 403 NOT_RECIPIENT (DL-F07-03)."""
    with patch(
        "app.routers.seen.seen_service.mark_seen",
        side_effect=NotRecipientError(),
    ):
        resp = client.post(f"/posts/{_POST_ID}/seen", headers=_HEADERS)

    assert resp.status_code == 403
    assert resp.json()["error_code"] == "NOT_RECIPIENT"


def test_mark_seen_post_not_found_404(client: TestClient) -> None:
    """An unknown post → 404 POST_NOT_FOUND."""
    with patch(
        "app.routers.seen.seen_service.mark_seen",
        side_effect=PostNotFoundError(),
    ):
        resp = client.post(f"/posts/{_POST_ID}/seen", headers=_HEADERS)

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "POST_NOT_FOUND"


def test_mark_seen_user_not_found_404(empty_client: TestClient) -> None:
    """Viewer without a user row → 404 USER_NOT_FOUND (DL-F07-09)."""
    resp = empty_client.post(f"/posts/{_POST_ID}/seen", headers=_HEADERS)

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "USER_NOT_FOUND"


# --- GET /posts/{id}/seen-by -------------------------------------------


def test_seen_by_200(client: TestClient) -> None:
    """Sender → 200 with {post_id, seen_count, viewers} (AC-F07-2)."""
    viewers = [
        {
            "user_id": str(uuid.uuid4()),
            "display_name": "Châu",
            "avatar_url": None,
            "seen_at": _SEEN_AT,
        }
    ]
    with patch(
        "app.routers.seen.seen_service.get_seen_by",
        return_value=(viewers, 1),
    ):
        resp = client.get(f"/posts/{_POST_ID}/seen-by", headers=_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["post_id"] == _POST_ID
    assert body["seen_count"] == 1
    assert body["viewers"][0]["display_name"] == "Châu"


def test_seen_by_not_sender_403(client: TestClient) -> None:
    """A non-sender → 403 FORBIDDEN (DL-F07-04)."""
    with patch(
        "app.routers.seen.seen_service.get_seen_by",
        side_effect=NotSenderError(),
    ):
        resp = client.get(f"/posts/{_POST_ID}/seen-by", headers=_HEADERS)

    assert resp.status_code == 403
    assert resp.json()["error_code"] == "FORBIDDEN"


def test_seen_by_post_not_found_404(client: TestClient) -> None:
    """An unknown post → 404 POST_NOT_FOUND."""
    with patch(
        "app.routers.seen.seen_service.get_seen_by",
        side_effect=PostNotFoundError(),
    ):
        resp = client.get(f"/posts/{_POST_ID}/seen-by", headers=_HEADERS)

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "POST_NOT_FOUND"


def test_seen_by_empty_200(client: TestClient) -> None:
    """Nobody seen → 200 with seen_count=0, viewers=[]."""
    with patch(
        "app.routers.seen.seen_service.get_seen_by",
        return_value=([], 0),
    ):
        resp = client.get(f"/posts/{_POST_ID}/seen-by", headers=_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["seen_count"] == 0
    assert body["viewers"] == []
