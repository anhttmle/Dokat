"""Integration tests: end-to-end seen flow (F07).

Run with: make test-integration

Requires (see tests/integration/conftest.py):
  - Firebase Auth Emulator at $FIREBASE_AUTH_EMULATOR_HOST
  - PostgreSQL test DB at $TEST_DATABASE_URL with tables created

Each test creates real users via the emulator + POST /auth/session,
seeds friendships directly, creates a post through the real
``post_service``, then marks seen and reads seen-by over the real
router / service / PostgreSQL stack.

Refs: Design §6.6, §6.7; FR-2, FR-3, FR-4;
AC-F07-1, AC-F07-2, AC-F07-3; DL-F07-02, DL-F07-04
"""

import os
import uuid

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.friendship import Friendship
from app.services import post_service

_EMULATOR_HOST = os.environ.get(
    "FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099"
)
_IDP_BASE = f"http://{_EMULATOR_HOST}/identitytoolkit.googleapis.com/v1"
_API_KEY = "fake-api-key"


def _create_anonymous_user() -> str:
    """Create an anonymous Firebase user via the emulator; return token."""
    resp = httpx.post(
        f"{_IDP_BASE}/accounts:signUp?key={_API_KEY}",
        json={"returnSecureToken": True},
    )
    resp.raise_for_status()
    return resp.json()["idToken"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_user(client: TestClient, token: str) -> str:
    """Create the DB user row via POST /auth/session; return its UUID."""
    resp = client.post("/auth/session", headers=_auth(token))
    assert resp.status_code == 200
    return resp.json()["user_id"]


def _seed_friendship(db: Session, a_id: str, b_id: str) -> None:
    """Insert a canonical friendship edge between two user UUIDs."""
    uid_a, uid_b = sorted([a_id, b_id])
    db.add(
        Friendship(
            user_id_a=uuid.UUID(uid_a),
            user_id_b=uuid.UUID(uid_b),
        )
    )
    db.commit()


def test_recipient_seen_appears_for_sender(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """B sees A's photo → A's seen-by lists B (AC-F07-1, AC-F07-2)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    _seed_friendship(db_session, a_id, b_id)

    post, _ = post_service.create_post(
        db_session,
        user_id=a_id,
        s3_key="posts/a/1.jpg",
        cdn_url="https://cdn/a/1.jpg",
        recipient_ids=[b_id],
    )

    seen = integration_client.post(
        f"/posts/{post.id}/seen", headers=_auth(b_token)
    )
    assert seen.status_code == 200

    resp = integration_client.get(
        f"/posts/{post.id}/seen-by", headers=_auth(a_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["seen_count"] == 1
    assert body["viewers"][0]["user_id"] == b_id


def test_seen_no_duplicate_on_repeat(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """B sees twice → seen_count stays 1 (AC-F07-3, DL-F07-02)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    _seed_friendship(db_session, a_id, b_id)

    post, _ = post_service.create_post(
        db_session,
        user_id=a_id,
        s3_key="posts/a/2.jpg",
        cdn_url="https://cdn/a/2.jpg",
        recipient_ids=[b_id],
    )

    first = integration_client.post(
        f"/posts/{post.id}/seen", headers=_auth(b_token)
    )
    second = integration_client.post(
        f"/posts/{post.id}/seen", headers=_auth(b_token)
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["seen_at"] == second.json()["seen_at"]

    resp = integration_client.get(
        f"/posts/{post.id}/seen-by", headers=_auth(a_token)
    )
    assert resp.json()["seen_count"] == 1


def test_multiple_viewers_counted(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """B, C see; D does not → seen_count=2, D absent (AC-F07-2)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    c_token = _create_anonymous_user()
    c_id = _register_user(integration_client, c_token)
    d_token = _create_anonymous_user()
    d_id = _register_user(integration_client, d_token)
    for friend_id in (b_id, c_id, d_id):
        _seed_friendship(db_session, a_id, friend_id)

    post, _ = post_service.create_post(
        db_session,
        user_id=a_id,
        s3_key="posts/a/3.jpg",
        cdn_url="https://cdn/a/3.jpg",
        recipient_ids=[b_id, c_id, d_id],
    )

    assert (
        integration_client.post(
            f"/posts/{post.id}/seen", headers=_auth(b_token)
        ).status_code
        == 200
    )
    assert (
        integration_client.post(
            f"/posts/{post.id}/seen", headers=_auth(c_token)
        ).status_code
        == 200
    )

    resp = integration_client.get(
        f"/posts/{post.id}/seen-by", headers=_auth(a_token)
    )
    body = resp.json()
    ids = {v["user_id"] for v in body["viewers"]}
    assert body["seen_count"] == 2
    assert ids == {b_id, c_id}
    assert d_id not in ids


def test_non_sender_cannot_view_seen_by(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """B calls A's seen-by → 403 FORBIDDEN (DL-F07-04)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    _seed_friendship(db_session, a_id, b_id)

    post, _ = post_service.create_post(
        db_session,
        user_id=a_id,
        s3_key="posts/a/4.jpg",
        cdn_url="https://cdn/a/4.jpg",
        recipient_ids=[b_id],
    )

    resp = integration_client.get(
        f"/posts/{post.id}/seen-by", headers=_auth(b_token)
    )
    assert resp.status_code == 403
    assert resp.json()["error_code"] == "FORBIDDEN"
