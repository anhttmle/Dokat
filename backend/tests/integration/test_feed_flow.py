"""Integration tests: end-to-end GET /feed flow (F06).

Run with: make test-integration

Requires (see tests/integration/conftest.py):
  - Firebase Auth Emulator at $FIREBASE_AUTH_EMULATOR_HOST
  - PostgreSQL test DB at $TEST_DATABASE_URL with tables created

Each test creates real users via the emulator + POST /auth/session,
seeds friendships directly, creates posts through the real service, then
reads them back over the real GET /feed router / service / PostgreSQL
stack.

Refs: Design §6.8, §6.9; FR-2; AC-F06-1, AC-F06-2, AC-F06-6;
DL-F06-01, DL-F06-04
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


def test_received_post_appears_on_feed(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """A sends to B → B's feed contains the post (AC-F06-1)."""
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

    resp = integration_client.get("/feed", headers=_auth(b_token))
    assert resp.status_code == 200
    ids = [i["post_id"] for i in resp.json()["items"]]
    assert str(post.id) in ids


def test_expired_post_hidden(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """A post past its expires_at is not on the feed (AC-F06-2)."""
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

    resp = integration_client.get("/feed", headers=_auth(b_token))
    assert resp.status_code == 200
    ids = [i["post_id"] for i in resp.json()["items"]]
    assert str(post.id) not in ids


def test_feed_chronological_order(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """Multiple posts come back newest first (AC-F06-6)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    _seed_friendship(db_session, a_id, b_id)

    now = datetime.now(UTC)
    ids: list[str] = []
    for i in range(3):
        post = Post(
            user_id=uuid.UUID(a_id),
            s3_key=f"posts/a/{i}.jpg",
            cdn_url=f"https://cdn/a/{i}.jpg",
            expires_at=now + timedelta(hours=24),
            created_at=now - timedelta(minutes=i),
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        db_session.add(
            PostRecipient(post_id=post.id, recipient_id=uuid.UUID(b_id))
        )
        db_session.commit()
        ids.append(str(post.id))

    resp = integration_client.get("/feed", headers=_auth(b_token))
    assert resp.status_code == 200
    returned = [i["post_id"] for i in resp.json()["items"]]
    # ids[0] is newest (created now); expect newest-first order.
    assert returned == ids


def test_non_recipient_does_not_see(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """A user who is not a recipient never sees the post (FR-2)."""
    a_token = _create_anonymous_user()
    a_id = _register_user(integration_client, a_token)
    b_token = _create_anonymous_user()
    b_id = _register_user(integration_client, b_token)
    c_token = _create_anonymous_user()
    _register_user(integration_client, c_token)
    _seed_friendship(db_session, a_id, b_id)

    post, _ = post_service.create_post(
        db_session,
        user_id=a_id,
        s3_key="posts/a/2.jpg",
        cdn_url="https://cdn/a/2.jpg",
        recipient_ids=[b_id],
    )

    resp = integration_client.get("/feed", headers=_auth(c_token))
    assert resp.status_code == 200
    ids = [i["post_id"] for i in resp.json()["items"]]
    assert str(post.id) not in ids
