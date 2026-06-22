"""Integration tests: end-to-end POST /posts create flow (F05).

Run with: make test-integration

Requires (see tests/integration/conftest.py):
  - Firebase Auth Emulator at $FIREBASE_AUTH_EMULATOR_HOST
  - PostgreSQL test DB at $TEST_DATABASE_URL with tables created

Each test creates real users via the emulator + POST /auth/session,
seeds friendships directly in the DB, then drives the real router /
service / PostgreSQL stack. Recipients must be friends (DL-F05-07), so
friendships are inserted before sending.

Refs: Design §6.6, §6.7; AC-F05-2, AC-F05-3, AC-F05-4;
F11 AC-F11-1, AC-F11-3; DL-F05-01
"""

import os
import uuid

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.friendship import Friendship
from app.models.post import Post
from app.models.post_recipient import PostRecipient

_EMULATOR_HOST = os.environ.get(
    "FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099"
)
_IDP_BASE = f"http://{_EMULATOR_HOST}/identitytoolkit.googleapis.com/v1"
_API_KEY = "fake-api-key"


def _create_anonymous_user() -> str:
    """Create an anonymous Firebase user via the emulator REST API.

    Returns:
        The Firebase ID token.
    """
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


def test_broadcast_creates_post_and_recipients(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """POST /posts with N friends → 1 post + N recipients (AC-F05-2)."""
    sender_token = _create_anonymous_user()
    sender_id = _register_user(integration_client, sender_token)

    friend_ids = []
    for _ in range(2):
        ftoken = _create_anonymous_user()
        fid = _register_user(integration_client, ftoken)
        _seed_friendship(db_session, sender_id, fid)
        friend_ids.append(fid)

    resp = integration_client.post(
        "/posts",
        headers=_auth(sender_token),
        json={
            "s3_key": "posts/s/1.jpg",
            "cdn_url": "https://cdn/s/1.jpg",
            "recipient_ids": friend_ids,
        },
    )

    assert resp.status_code == 201
    assert resp.json()["recipient_count"] == 2

    db_session.expire_all()
    post = (
        db_session.query(Post)
        .filter(Post.user_id == uuid.UUID(sender_id))
        .one()
    )
    rows = (
        db_session.query(PostRecipient)
        .filter(PostRecipient.post_id == post.id)
        .all()
    )
    assert {str(r.recipient_id) for r in rows} == set(friend_ids)


def test_subset_creates_only_selected(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """A chosen subset gets recipients; others do not (AC-F05-3)."""
    sender_token = _create_anonymous_user()
    sender_id = _register_user(integration_client, sender_token)

    friend_ids = []
    for _ in range(3):
        ftoken = _create_anonymous_user()
        fid = _register_user(integration_client, ftoken)
        _seed_friendship(db_session, sender_id, fid)
        friend_ids.append(fid)

    subset = friend_ids[:2]
    resp = integration_client.post(
        "/posts",
        headers=_auth(sender_token),
        json={
            "s3_key": "posts/s/2.jpg",
            "cdn_url": "https://cdn/s/2.jpg",
            "recipient_ids": subset,
        },
    )

    assert resp.status_code == 201
    assert resp.json()["recipient_count"] == 2

    db_session.expire_all()
    post = (
        db_session.query(Post)
        .filter(Post.user_id == uuid.UUID(sender_id))
        .one()
    )
    stored = {
        str(r.recipient_id)
        for r in db_session.query(PostRecipient)
        .filter(PostRecipient.post_id == post.id)
        .all()
    }
    assert stored == set(subset)


def test_zero_recipient_persists_post(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """0 recipients → post persisted, 0 recipient rows (AC-F05-4)."""
    sender_token = _create_anonymous_user()
    sender_id = _register_user(integration_client, sender_token)

    resp = integration_client.post(
        "/posts",
        headers=_auth(sender_token),
        json={
            "s3_key": "posts/s/3.jpg",
            "cdn_url": "https://cdn/s/3.jpg",
            "recipient_ids": [],
        },
    )

    assert resp.status_code == 201
    assert resp.json()["recipient_count"] == 0

    db_session.expire_all()
    post = (
        db_session.query(Post)
        .filter(Post.user_id == uuid.UUID(sender_id))
        .one()
    )
    assert (
        db_session.query(PostRecipient)
        .filter(PostRecipient.post_id == post.id)
        .count()
        == 0
    )


def test_latlng_persisted_not_exposed(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """lat/lng stored at 8-digit precision but absent from the response.

    Refs: F11 AC-F11-1, AC-F11-3
    """
    sender_token = _create_anonymous_user()
    sender_id = _register_user(integration_client, sender_token)

    resp = integration_client.post(
        "/posts",
        headers=_auth(sender_token),
        json={
            "s3_key": "posts/s/4.jpg",
            "cdn_url": "https://cdn/s/4.jpg",
            "recipient_ids": [],
            "latitude": 10.77621500,
            "longitude": 106.69505800,
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert "latitude" not in body
    assert "longitude" not in body

    db_session.expire_all()
    post = (
        db_session.query(Post)
        .filter(Post.user_id == uuid.UUID(sender_id))
        .one()
    )
    assert float(post.latitude) == 10.77621500
    assert float(post.longitude) == 106.69505800
