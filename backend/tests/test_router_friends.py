"""API-level tests for the friends router (/friends).

Written TDD-style; tests are expected to FAIL until the router and
services are implemented in later F03 tasks.

Uses ``pytest-mock`` to mock the service layer.

Refs: Design §3, §6.2, AC-F03-1 through AC-F03-9
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.friendship  # noqa: F401  register table on Base
from app.main import app
from app.models.user import Base, OAuthProvider, User, UserProvider
from app.routers.auth import get_db
from app.schemas.friend import GenerateQRResponse
from app.services.friend_service import (
    AlreadyFriendsError,
    FriendLimitError,
    SelfFriendError,
    UserNotFoundError,
)
from app.services.otp_service import (
    OTPExpiredError,
    OTPPayload,
    OTPUsedError,
)

_HEADERS = {"Authorization": "Bearer fake-token"}

_FAKE_QR = {
    "token": "550e8400-e29b-41d4-a716-446655440000",
    "deep_link": (
        "https://petapp.example.com/add-friend"
        "?token=550e8400-e29b-41d4-a716-446655440000"
    ),
    "expires_at": "2026-06-21T04:05:00Z",
}

_FAKE_FRIEND = {
    "user_id": "abc-friend-uuid",
    "display_name": "Nguyen Van A",
    "avatar_url": None,
}

_FAKE_SCAN_RESPONSE = {
    "friendship_id": "friend-row-uuid",
    "friend": _FAKE_FRIEND,
    "created_at": "2026-06-21T04:02:30Z",
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
def client(db_session: Session, mock_verify_id_token: MagicMock) -> TestClient:
    """TestClient with DB overridden and Firebase token mocked."""
    _ensure_user(db_session, firebase_uid="test-uid-anonymous")
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _ensure_user(db: Session, *, firebase_uid: str) -> User:
    """Insert user if not already present."""
    existing = db.query(User).filter(
        User.firebase_uid == firebase_uid
    ).first()
    if existing:
        return existing
    now = datetime.now(timezone.utc)
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
# POST /friends/qr/generate
# ---------------------------------------------------------------------------


def test_generate_qr_success(client: TestClient) -> None:
    """200 response with token, deep_link, expires_at."""
    fake_response = GenerateQRResponse(**_FAKE_QR)
    mock_svc = MagicMock()
    mock_svc.generate = AsyncMock(return_value=fake_response)
    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_svc
    ):
        resp = client.post("/friends/qr/generate", headers=_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert "deep_link" in body
    assert "expires_at" in body


def test_generate_qr_unauthenticated() -> None:
    """Missing Authorization header returns 401."""
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.post("/friends/qr/generate")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /friends/qr/scan
# ---------------------------------------------------------------------------


def test_scan_qr_success(client: TestClient) -> None:
    """201 response with friendship_id and friend info."""
    mock_svc = MagicMock()
    mock_svc.consume = AsyncMock(
        return_value=OTPPayload(initiator_id="abc-friend-uuid")
    )
    mock_notif_instance = MagicMock()
    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_svc
    ), patch(
        "app.routers.friends.create_friendship",
        return_value=MagicMock(
            id="friend-row-uuid",
            created_at=datetime(2026, 6, 21, 4, 2, 30, tzinfo=timezone.utc),
        ),
    ), patch(
        "app.routers.friends.get_friend_profile",
        return_value=_FAKE_FRIEND,
    ), patch(
        "app.routers.friends.NotificationService",
        return_value=mock_notif_instance,
    ):
        resp = client.post(
            "/friends/qr/scan",
            json={"token": "550e8400-e29b-41d4-a716-446655440000"},
            headers=_HEADERS,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert "friendship_id" in body
    assert "friend" in body


def test_scan_qr_expired(client: TestClient) -> None:
    """410 with error_code QR_EXPIRED."""
    mock_svc = MagicMock()
    mock_svc.consume = AsyncMock(side_effect=OTPExpiredError())
    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_svc
    ):
        resp = client.post(
            "/friends/qr/scan",
            json={"token": "expired-token"},
            headers=_HEADERS,
        )

    assert resp.status_code == 410
    assert resp.json()["error_code"] == "QR_EXPIRED"


def test_scan_qr_used(client: TestClient) -> None:
    """410 with error_code QR_USED."""
    mock_svc = MagicMock()
    mock_svc.consume = AsyncMock(side_effect=OTPUsedError())
    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_svc
    ):
        resp = client.post(
            "/friends/qr/scan",
            json={"token": "used-token"},
            headers=_HEADERS,
        )

    assert resp.status_code == 410
    assert resp.json()["error_code"] == "QR_USED"


def test_scan_qr_self(client: TestClient) -> None:
    """422 with error_code SELF_FRIEND."""
    mock_svc = MagicMock()
    mock_svc.consume = AsyncMock(
        return_value=OTPPayload(initiator_id="self-uuid")
    )
    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_svc
    ), patch(
        "app.routers.friends.create_friendship",
        side_effect=SelfFriendError(),
    ):
        resp = client.post(
            "/friends/qr/scan",
            json={"token": "self-token"},
            headers=_HEADERS,
        )

    assert resp.status_code == 422
    assert resp.json()["error_code"] == "SELF_FRIEND"


def test_scan_qr_already_friends(client: TestClient) -> None:
    """409 when both users are already friends."""
    mock_svc = MagicMock()
    mock_svc.consume = AsyncMock(
        return_value=OTPPayload(initiator_id="other-uuid")
    )
    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_svc
    ), patch(
        "app.routers.friends.create_friendship",
        side_effect=AlreadyFriendsError(),
    ):
        resp = client.post(
            "/friends/qr/scan",
            json={"token": "dup-token"},
            headers=_HEADERS,
        )

    assert resp.status_code == 409


def test_scan_qr_limit_initiator(client: TestClient) -> None:
    """422 with error_code FRIEND_LIMIT_INITIATOR."""
    mock_svc = MagicMock()
    mock_svc.consume = AsyncMock(
        return_value=OTPPayload(initiator_id="full-uuid")
    )
    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_svc
    ), patch(
        "app.routers.friends.create_friendship",
        side_effect=FriendLimitError(side="initiator"),
    ):
        resp = client.post(
            "/friends/qr/scan",
            json={"token": "limit-token"},
            headers=_HEADERS,
        )

    assert resp.status_code == 422
    assert resp.json()["error_code"] == "FRIEND_LIMIT_INITIATOR"


def test_scan_qr_limit_scanner(client: TestClient) -> None:
    """422 with error_code FRIEND_LIMIT_SCANNER."""
    mock_svc = MagicMock()
    mock_svc.consume = AsyncMock(
        return_value=OTPPayload(initiator_id="other-uuid")
    )
    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_svc
    ), patch(
        "app.routers.friends.create_friendship",
        side_effect=FriendLimitError(side="scanner"),
    ):
        resp = client.post(
            "/friends/qr/scan",
            json={"token": "limit-scan-token"},
            headers=_HEADERS,
        )

    assert resp.status_code == 422
    assert resp.json()["error_code"] == "FRIEND_LIMIT_SCANNER"


# ---------------------------------------------------------------------------
# GET /friends
# ---------------------------------------------------------------------------


def test_get_friends_list(client: TestClient) -> None:
    """200 with friends list, correct total and user_id."""
    with patch(
        "app.routers.friends.list_friends",
        return_value=[
            {
                "user_id": "abc-uuid",
                "display_name": "Tran Thi B",
                "avatar_url": None,
                "friendship_created_at": "2026-06-20T10:00:00Z",
            }
        ],
    ):
        resp = client.get("/friends", headers=_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["friends"][0]["user_id"] == "abc-uuid"


def test_get_friends_unauthenticated() -> None:
    """Missing Authorization header returns 401."""
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/friends")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /friends/{friend_user_id}
# ---------------------------------------------------------------------------


def test_delete_friend_success(client: TestClient) -> None:
    """204 when friendship is deleted."""
    with patch(
        "app.routers.friends.get_friend_profile",
        return_value=_FAKE_FRIEND,
    ), patch("app.routers.friends.delete_friendship", return_value=None):
        resp = client.delete(
            "/friends/some-friend-uuid", headers=_HEADERS
        )

    assert resp.status_code == 204


def test_delete_friend_not_found(client: TestClient) -> None:
    """204 even when friendship does not exist (idempotent)."""
    with patch(
        "app.routers.friends.get_friend_profile",
        return_value=_FAKE_FRIEND,
    ), patch("app.routers.friends.delete_friendship", return_value=None):
        resp = client.delete(
            "/friends/nonexistent-uuid", headers=_HEADERS
        )

    assert resp.status_code == 204


def test_delete_friend_user_not_found(client: TestClient) -> None:
    """404 with USER_NOT_FOUND when friend_user_id is not in users table."""
    with patch(
        "app.routers.friends.get_friend_profile",
        side_effect=UserNotFoundError(),
    ):
        resp = client.delete(
            "/friends/nonexistent-uuid", headers=_HEADERS
        )

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "USER_NOT_FOUND"


def test_delete_friend_unauthenticated() -> None:
    """Missing Authorization header returns 401."""
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.delete("/friends/some-uuid")

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /friends/fcm-token
# ---------------------------------------------------------------------------


def test_put_fcm_token(client: TestClient) -> None:
    """204 when FCM token is saved successfully."""
    with patch(
        "app.routers.friends.save_fcm_token", return_value=None
    ):
        resp = client.put(
            "/friends/fcm-token",
            json={"fcm_token": "cXV4eW..."},
            headers=_HEADERS,
        )

    assert resp.status_code == 204


def test_put_fcm_token_empty(client: TestClient) -> None:
    """422 when fcm_token is an empty string."""
    resp = client.put(
        "/friends/fcm-token",
        json={"fcm_token": ""},
        headers=_HEADERS,
    )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Notification behaviour on POST /friends/qr/scan
# ---------------------------------------------------------------------------

_FAKE_FRIENDSHIP = MagicMock(
    id="friend-row-uuid",
    created_at=datetime(2026, 6, 21, 4, 2, 30, tzinfo=timezone.utc),
)


def test_notification_sent_on_scan(client: TestClient) -> None:
    """NotificationService.send_new_friend is called once on success."""
    mock_otp_svc = MagicMock()
    mock_otp_svc.consume = AsyncMock(
        return_value=OTPPayload(initiator_id="abc-friend-uuid")
    )
    mock_notif_instance = MagicMock()

    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_otp_svc
    ), patch(
        "app.routers.friends.create_friendship",
        return_value=_FAKE_FRIENDSHIP,
    ), patch(
        "app.routers.friends.get_friend_profile",
        return_value=_FAKE_FRIEND,
    ), patch(
        "app.routers.friends.NotificationService",
        return_value=mock_notif_instance,
    ):
        resp = client.post(
            "/friends/qr/scan",
            json={"token": "valid-token"},
            headers=_HEADERS,
        )

    assert resp.status_code == 201
    mock_notif_instance.send_new_friend.assert_called_once()


def test_notification_failure_does_not_rollback(
    client: TestClient,
) -> None:
    """201 is returned even when NotificationService.send_new_friend raises."""
    mock_otp_svc = MagicMock()
    mock_otp_svc.consume = AsyncMock(
        return_value=OTPPayload(initiator_id="abc-friend-uuid")
    )
    mock_notif_instance = MagicMock()
    mock_notif_instance.send_new_friend.side_effect = Exception(
        "FCM unavailable"
    )

    with patch("app.routers.friends.get_redis_client"), patch(
        "app.routers.friends.OTPService", return_value=mock_otp_svc
    ), patch(
        "app.routers.friends.create_friendship",
        return_value=_FAKE_FRIENDSHIP,
    ), patch(
        "app.routers.friends.get_friend_profile",
        return_value=_FAKE_FRIEND,
    ), patch(
        "app.routers.friends.NotificationService",
        return_value=mock_notif_instance,
    ):
        resp = client.post(
            "/friends/qr/scan",
            json={"token": "valid-token"},
            headers=_HEADERS,
        )

    assert resp.status_code == 201
