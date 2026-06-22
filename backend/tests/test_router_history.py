"""API-level tests for the history router (GET /history/sent|received).

Mocks history_service and uses SQLite in-memory for the resolved-user
lookup (mirrors test_router_feed.py). Firebase token verification is
mocked via the shared ``mock_verify_id_token`` fixture.

Refs: Design §3.1, §3.2, §6.4; FR-1; AC-F08-2, AC-F08-4;
DL-F08-04, DL-F08-07
"""

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
from app.services.history_service import InvalidCursorError

_HEADERS = {"Authorization": "Bearer fake-token"}

_SENT_ITEM = {
    "post_id": "11111111-1111-1111-1111-111111111111",
    "cdn_url": "https://cdn/x.jpg",
    "created_at": "2026-06-22T07:00:00+00:00",
    "recipient_count": 3,
    "seen_count": 2,
}

_RECEIVED_ITEM = {
    "post_id": "22222222-2222-2222-2222-222222222222",
    "sender_id": "33333333-3333-3333-3333-333333333333",
    "sender_display_name": "Anh",
    "sender_avatar_url": None,
    "pet_name": "Mướp",
    "cdn_url": "https://cdn/y.jpg",
    "created_at": "2026-06-22T07:00:00+00:00",
    "seen": True,
}


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


def test_sent_200(client: TestClient) -> None:
    """200 with {items, next_cursor} matching the schema (AC-F08-2)."""
    with patch(
        "app.routers.history.history_service.get_sent",
        return_value=([_SENT_ITEM], "next-cursor-token"),
    ):
        resp = client.get("/history/sent", headers=_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["next_cursor"] == "next-cursor-token"
    assert len(body["items"]) == 1
    assert body["items"][0]["post_id"] == _SENT_ITEM["post_id"]
    assert body["items"][0]["recipient_count"] == 3
    assert body["items"][0]["seen_count"] == 2


def test_received_200(client: TestClient) -> None:
    """200 with {items, next_cursor} matching the schema (AC-F08-2)."""
    with patch(
        "app.routers.history.history_service.get_received",
        return_value=([_RECEIVED_ITEM], None),
    ):
        resp = client.get("/history/received", headers=_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["next_cursor"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["post_id"] == _RECEIVED_ITEM["post_id"]
    assert body["items"][0]["pet_name"] == "Mướp"


def test_sent_user_not_found_404(empty_client: TestClient) -> None:
    """Viewer without a user row → 404 USER_NOT_FOUND (DL-F08-07)."""
    resp = empty_client.get("/history/sent", headers=_HEADERS)
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "USER_NOT_FOUND"


def test_received_user_not_found_404(empty_client: TestClient) -> None:
    """Viewer without a user row → 404 USER_NOT_FOUND (DL-F08-07)."""
    resp = empty_client.get("/history/received", headers=_HEADERS)
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "USER_NOT_FOUND"


def test_invalid_cursor_400(client: TestClient) -> None:
    """A malformed cursor → 400 INVALID_CURSOR (DL-F08-04)."""
    with patch(
        "app.routers.history.history_service.get_sent",
        side_effect=InvalidCursorError(),
    ):
        resp = client.get("/history/sent?cursor=bad", headers=_HEADERS)

    assert resp.status_code == 400
    assert resp.json()["error_code"] == "INVALID_CURSOR"


def test_sent_empty_200(client: TestClient) -> None:
    """Empty sent history → 200 with items=[] (AC-F08-4)."""
    with patch(
        "app.routers.history.history_service.get_sent",
        return_value=([], None),
    ):
        resp = client.get("/history/sent", headers=_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["next_cursor"] is None
