"""Integration tests: end-to-end history flow (F08).

Run with: make test-integration

Requires (see tests/integration/conftest.py):
  - Firebase Auth Emulator at $FIREBASE_AUTH_EMULATOR_HOST
  - PostgreSQL test DB at $TEST_DATABASE_URL with tables created

Each test creates real users via the emulator + POST /auth/session,
seeds friendships directly, creates posts through the real
``post_service``, optionally marks seen via ``seen_service``, then reads
them back over the real GET /history/* router / service / PostgreSQL
stack.

Refs: Design §6.8, §6.9; FR-2, FR-5;
AC-F08-1, AC-F08-2, AC-F08-3; DL-F08-01, DL-F08-05
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.friendship import Friendship
from app.models.post import Post
from app.models.post_recipient import PostRecipient
from app.services import post_service, seen_service

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


def test_sent_photo_appears_in_sent_history(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """A sends to B → A's sent history contains the post (AC-F08-2)."""
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

    resp = integration_client.get("/history/sent", headers=_auth(a_token))
    assert resp.status_code == 200
    items = resp.json()["items"]
    ids = [i["post_id"] for i in items]
    assert str(post.id) in ids
    item = next(i for i in items if i["post_id"] == str(post.id))
    assert item["recipient_count"] == 1


def test_received_photo_appears_in_received_history(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """A sends to B → B's received history contains the post (AC-F08-2)."""
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

    resp = integration_client.get("/history/received", headers=_auth(b_token))
    assert resp.status_code == 200
    ids = [i["post_id"] for i in resp.json()["items"]]
    assert str(post.id) in ids


def test_expired_photo_hidden_in_history(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """An expired post is absent from both histories (AC-F08-1)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    _seed_friendship(db_session, a_id, b_id)

    now = datetime.now(UTC)
    post = Post(
        user_id=uuid.UUID(a_id),
        s3_key="posts/a/old.jpg",
        cdn_url="https://cdn/a/old.jpg",
        expires_at=now - timedelta(hours=1),
        created_at=now - timedelta(hours=25),
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    db_session.add(
        PostRecipient(post_id=post.id, recipient_id=uuid.UUID(b_id))
    )
    db_session.commit()

    sent = integration_client.get("/history/sent", headers=_auth(a_token))
    received = integration_client.get(
        "/history/received", headers=_auth(b_token)
    )
    assert str(post.id) not in [i["post_id"] for i in sent.json()["items"]]
    assert str(post.id) not in [i["post_id"] for i in received.json()["items"]]


def test_sent_seen_count_reflects_viewers(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """B views A's photo → A's sent seen_count = 1 (FR-5, AC-F08-3)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    _seed_friendship(db_session, a_id, b_id)

    post, _ = post_service.create_post(
        db_session,
        user_id=a_id,
        s3_key="posts/a/3.jpg",
        cdn_url="https://cdn/a/3.jpg",
        recipient_ids=[b_id],
    )

    seen_service.mark_seen(db_session, post_id=str(post.id), viewer_id=b_id)

    resp = integration_client.get("/history/sent", headers=_auth(a_token))
    assert resp.status_code == 200
    item = next(
        i for i in resp.json()["items"] if i["post_id"] == str(post.id)
    )
    assert item["recipient_count"] == 1
    assert item["seen_count"] == 1
