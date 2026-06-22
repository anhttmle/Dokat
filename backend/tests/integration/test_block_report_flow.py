"""Integration tests: end-to-end block / report flow (F10).

Run with: make test-integration

Requires (see tests/integration/conftest.py):
  - Firebase Auth Emulator at $FIREBASE_AUTH_EMULATOR_HOST
  - PostgreSQL test DB at $TEST_DATABASE_URL with tables created

Each test creates real users via the emulator + POST /auth/session,
seeds a friendship directly, creates posts through the real service, then
exercises the real /users/* router over the full PostgreSQL stack.

Refs: Design §6.11, §6.12; FR-4, FR-7, FR-8; AC-F10-3, AC-F10-5;
DL-F10-04, DL-F10-10
"""

import os
import uuid

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.friendship import Friendship
from app.models.report import Report
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


def test_block_then_feed_hidden(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """B sends to A → A blocks B → B's post leaves A's feed (AC-F10-3)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    _seed_friendship(db_session, a_id, b_id)

    post, _ = post_service.create_post(
        db_session,
        user_id=b_id,
        s3_key="posts/b/1.jpg",
        cdn_url="https://cdn/b/1.jpg",
        recipient_ids=[a_id],
    )

    before = integration_client.get("/feed", headers=_auth(a_token))
    assert str(post.id) in [i["post_id"] for i in before.json()["items"]]

    resp = integration_client.post(
        "/users/block", json={"user_id": b_id}, headers=_auth(a_token)
    )
    assert resp.status_code == 201

    after = integration_client.get("/feed", headers=_auth(a_token))
    assert str(post.id) not in [i["post_id"] for i in after.json()["items"]]


def test_block_then_not_friends(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """Blocking removes the friendship → B leaves A's /friends (DL-F10-10)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    _seed_friendship(db_session, a_id, b_id)

    resp = integration_client.post(
        "/users/block", json={"user_id": b_id}, headers=_auth(a_token)
    )
    assert resp.status_code == 201

    friends = integration_client.get("/friends", headers=_auth(a_token))
    assert friends.status_code == 200
    ids = [f["user_id"] for f in friends.json()["friends"]]
    assert b_id not in ids


def test_report_persists(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """Report B → row stored; B still appears normally (AC-F10-5)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    _seed_friendship(db_session, a_id, b_id)

    resp = integration_client.post(
        "/users/report",
        json={"user_id": b_id, "reason": "spam"},
        headers=_auth(a_token),
    )
    assert resp.status_code == 201

    stored = (
        db_session.query(Report)
        .filter(
            Report.reporter_id == uuid.UUID(a_id),
            Report.reported_user_id == uuid.UUID(b_id),
        )
        .first()
    )
    assert stored is not None

    # Report does not block: B remains in A's friend list (AC-F10-5).
    friends = integration_client.get("/friends", headers=_auth(a_token))
    ids = [f["user_id"] for f in friends.json()["friends"]]
    assert b_id in ids
