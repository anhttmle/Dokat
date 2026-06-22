"""API-level tests for the settings router (/users).

Mirrors ``test_router_friends.py``: SQLite in-memory DB overriding
``get_db`` and a mocked Firebase token. Service functions are patched in
the router namespace so the router's exception → error-code mapping is
exercised in isolation.

Refs: Design §3, §5, §6.5; FR-3, FR-4, FR-6, FR-9;
AC-F10-2, AC-F10-3, AC-F10-4, AC-F10-5, AC-F10-6; DL-F10-08
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.user import Base, User
from app.routers.auth import get_db
from app.services.account_service import (
    LastProviderError,
    ProviderNotLinkedError,
)
from app.services.block_service import NotFriendsError, SelfBlockError
from app.services.friend_service import UserNotFoundError
from app.services.report_service import InvalidReasonError, SelfReportError

_HEADERS = {"Authorization": "Bearer fake-token"}
_OTHER = "11111111-1111-1111-1111-111111111111"


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
def client(db_session: Session, mock_verify_id_token: MagicMock) -> TestClient:
    """TestClient with DB overridden and Firebase token mocked."""
    _ensure_user(db_session, firebase_uid="test-uid-anonymous")
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _ensure_user(db: Session, *, firebase_uid: str) -> User:
    """Insert user if not already present."""
    existing = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if existing:
        return existing
    now = datetime.now(UTC)
    user = User(
        firebase_uid=firebase_uid,
        is_anonymous=False,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# POST /users/block
# ---------------------------------------------------------------------------


def test_block_201(client: TestClient) -> None:
    """Blocking a friend returns 201 with blocked_user_id (AC-F10-3)."""
    with patch("app.routers.settings.block_user", return_value=None):
        resp = client.post(
            "/users/block", json={"user_id": _OTHER}, headers=_HEADERS
        )
    assert resp.status_code == 201
    assert resp.json()["blocked_user_id"] == _OTHER


def test_block_not_friends_422(client: TestClient) -> None:
    """Blocking a non-friend returns 422 NOT_FRIENDS (AC-F10-4)."""
    with patch(
        "app.routers.settings.block_user", side_effect=NotFriendsError()
    ):
        resp = client.post(
            "/users/block", json={"user_id": _OTHER}, headers=_HEADERS
        )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "NOT_FRIENDS"


def test_block_self_422(client: TestClient) -> None:
    """Blocking oneself returns 422 SELF_BLOCK."""
    with patch(
        "app.routers.settings.block_user", side_effect=SelfBlockError()
    ):
        resp = client.post(
            "/users/block", json={"user_id": _OTHER}, headers=_HEADERS
        )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "SELF_BLOCK"


# ---------------------------------------------------------------------------
# DELETE /users/block/{user_id}
# ---------------------------------------------------------------------------


def test_unblock_204(client: TestClient) -> None:
    """Unblocking returns 204 (AC-F10-3)."""
    with patch("app.routers.settings.unblock_user", return_value=None):
        resp = client.delete(f"/users/block/{_OTHER}", headers=_HEADERS)
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# GET /users/block
# ---------------------------------------------------------------------------


def test_list_blocked_200(client: TestClient) -> None:
    """Listing blocked users returns 200 with blocked + total."""
    blocked = [
        {
            "user_id": _OTHER,
            "display_name": "Beta",
            "avatar_url": None,
            "blocked_at": datetime(2026, 6, 22, 7, 0, tzinfo=UTC),
        }
    ]
    with patch("app.routers.settings.list_blocked", return_value=blocked):
        resp = client.get("/users/block", headers=_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["blocked"][0]["user_id"] == _OTHER


# ---------------------------------------------------------------------------
# POST /users/report
# ---------------------------------------------------------------------------


def test_report_201(client: TestClient) -> None:
    """Reporting a user returns 201 with report_id (AC-F10-5)."""
    fake_report = MagicMock(id="report-uuid")
    with patch("app.routers.settings.report_user", return_value=fake_report):
        resp = client.post(
            "/users/report",
            json={"user_id": _OTHER, "reason": "spam"},
            headers=_HEADERS,
        )
    assert resp.status_code == 201
    assert resp.json()["report_id"] == "report-uuid"


def test_report_invalid_reason_422(client: TestClient) -> None:
    """An out-of-enum reason returns 422 INVALID_REASON."""
    with patch(
        "app.routers.settings.report_user",
        side_effect=InvalidReasonError(),
    ):
        resp = client.post(
            "/users/report",
            json={"user_id": _OTHER, "reason": "spam"},
            headers=_HEADERS,
        )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "INVALID_REASON"


def test_report_self_422(client: TestClient) -> None:
    """Reporting oneself returns 422 SELF_REPORT."""
    with patch(
        "app.routers.settings.report_user", side_effect=SelfReportError()
    ):
        resp = client.post(
            "/users/report",
            json={"user_id": _OTHER, "reason": "spam"},
            headers=_HEADERS,
        )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "SELF_REPORT"


# ---------------------------------------------------------------------------
# DELETE /users/providers/{provider}
# ---------------------------------------------------------------------------


def test_unlink_204(client: TestClient) -> None:
    """Unlinking with ≥2 providers returns 204 (FR-3)."""
    with patch("app.routers.settings.unlink_provider", return_value=None):
        resp = client.delete("/users/providers/google", headers=_HEADERS)
    assert resp.status_code == 204


def test_unlink_last_provider_422(client: TestClient) -> None:
    """Unlinking the last provider returns 422 LAST_PROVIDER (AC-F10-2)."""
    with patch(
        "app.routers.settings.unlink_provider",
        side_effect=LastProviderError(),
    ):
        resp = client.delete("/users/providers/apple", headers=_HEADERS)
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "LAST_PROVIDER"


def test_unlink_not_linked_404(client: TestClient) -> None:
    """Unlinking a provider not linked returns 404 PROVIDER_NOT_LINKED."""
    with patch(
        "app.routers.settings.unlink_provider",
        side_effect=ProviderNotLinkedError(),
    ):
        resp = client.delete("/users/providers/facebook", headers=_HEADERS)
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "PROVIDER_NOT_LINKED"


# ---------------------------------------------------------------------------
# POST /users/logout
# ---------------------------------------------------------------------------


def test_logout_204(client: TestClient) -> None:
    """Logout returns 204 and clears the device token (AC-F10-6)."""
    with patch(
        "app.routers.settings.clear_device_token", return_value=None
    ) as mock_clear:
        resp = client.post("/users/logout", headers=_HEADERS)
    assert resp.status_code == 204
    mock_clear.assert_called_once()


# ---------------------------------------------------------------------------
# Caller resolution (DL-F10-08)
# ---------------------------------------------------------------------------


def test_user_not_found_404(client: TestClient) -> None:
    """Caller without a user row returns 404 USER_NOT_FOUND (DL-F10-08)."""
    with patch(
        "app.routers.settings._get_user_id",
        side_effect=UserNotFoundError(),
    ):
        resp = client.post(
            "/users/block", json={"user_id": _OTHER}, headers=_HEADERS
        )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "USER_NOT_FOUND"


def test_unauthenticated_401() -> None:
    """Missing Authorization header returns 401."""
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.post("/users/block", json={"user_id": _OTHER})
    assert resp.status_code == 401
