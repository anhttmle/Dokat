"""Integration tests: full auth flow with Firebase Emulator + PostgreSQL.

Run with: make test-integration

All tests require:
  - Firebase Auth Emulator running at $FIREBASE_AUTH_EMULATOR_HOST
  - PostgreSQL test DB at $TEST_DATABASE_URL with tables created

Refs: FR-1, FR-3, FR-8; AC-F01-5, AC-F01-7, AC-F01-8
"""

import base64
import json
import os
import uuid

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import OAuthProvider, User, UserProvider

_EMULATOR_HOST = os.environ.get(
    "FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099"
)
_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "demo-test")
_IDP_BASE = f"http://{_EMULATOR_HOST}" f"/identitytoolkit.googleapis.com/v1"
_API_KEY = "fake-api-key"


# ── Emulator REST helpers ──────────────────────────────────────────────


def _b64url(data: dict) -> str:
    """Return URL-safe base64 of a JSON dict (no padding)."""
    return (
        base64.urlsafe_b64encode(json.dumps(data).encode())
        .rstrip(b"=")
        .decode()
    )


def _make_google_id_token(sub: str, email: str) -> str:
    """Return a minimal fake Google ID token accepted by the emulator.

    The emulator verifies JWT structure (header.payload.sig) but does
    NOT check the signature.  We use a static placeholder.
    """
    header = _b64url({"alg": "RS256", "kid": "fake-key-id"})
    payload = _b64url(
        {
            "iss": "https://accounts.google.com",
            "aud": _PROJECT_ID,
            "sub": sub,
            "email": email,
            "iat": 1_700_000_000,
            "exp": 9_999_999_999,
        }
    )
    return f"{header}.{payload}.fake-sig"


def _create_anonymous_user() -> tuple[str, str]:
    """Create an anonymous Firebase user via emulator REST API.

    Returns:
        (firebase_uid, id_token)
    """
    resp = httpx.post(
        f"{_IDP_BASE}/accounts:signUp?key={_API_KEY}",
        json={"returnSecureToken": True},
    )
    resp.raise_for_status()
    data = resp.json()
    return data["localId"], data["idToken"]


def _sign_in_with_google(
    google_sub: str,
    anon_id_token: str | None = None,
    email: str = "test@gmail.com",
) -> tuple[str, str]:
    """Sign in with Google via emulator (optionally linking to existing anon).

    When ``anon_id_token`` is provided, the Google identity is linked to
    the anonymous account (same firebase_uid is returned).  When omitted,
    a direct Google sign-in is performed (emulator looks up existing user
    by provider_uid / google_sub).

    Returns:
        (firebase_uid, id_token)
    """
    fake_google_token = _make_google_id_token(sub=google_sub, email=email)
    body: dict = {
        "postBody": (f"id_token={fake_google_token}&providerId=google.com"),
        "requestUri": "http://localhost",
        "returnSecureToken": True,
        "returnIdpCredential": True,
    }
    if anon_id_token:
        body["idToken"] = anon_id_token

    resp = httpx.post(
        f"{_IDP_BASE}/accounts:signInWithIdp?key={_API_KEY}",
        json=body,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["localId"], data["idToken"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ──────────────────────────────────────────────────────────────


def test_full_guest_session_flow(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """Anonymous token from emulator → POST /auth/session → 1 row in DB.

    Verifies:
      - Backend creates one ``users`` row with is_anonymous=True.
      - Response payload matches the created user.

    Refs: FR-1; AC-F01-1
    """
    firebase_uid, id_token = _create_anonymous_user()

    response = integration_client.post(
        "/auth/session", headers=_auth(id_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["firebase_uid"] == firebase_uid
    assert body["is_anonymous"] is True
    assert body["force_link_required"] is False
    assert "user_id" in body

    db_session.expire_all()
    user_count = db_session.query(User).count()
    assert user_count == 1

    user = (
        db_session.query(User)
        .filter(User.firebase_uid == firebase_uid)
        .first()
    )
    assert user is not None
    assert user.is_anonymous is True


def test_full_link_flow(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """Anonymous session → POST /auth/link (Google) → linked in DB.

    Verifies:
      - ``user_providers`` gains 1 row with provider=google.
      - ``users.is_anonymous`` flips to False.
      - ``user_id`` is unchanged throughout the flow.

    Refs: FR-8
    """
    # Step 1: anonymous user + session
    firebase_uid, anon_token = _create_anonymous_user()
    resp = integration_client.post("/auth/session", headers=_auth(anon_token))
    assert resp.status_code == 200
    user_id = resp.json()["user_id"]

    # Step 2: link Google via emulator
    google_sub = f"google-link-{uuid.uuid4().hex[:8]}"
    linked_uid, linked_token = _sign_in_with_google(
        google_sub=google_sub, anon_id_token=anon_token
    )
    assert linked_uid == firebase_uid  # same Firebase user after link

    # Step 3: notify backend of the link
    resp = integration_client.post("/auth/link", headers=_auth(linked_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["is_anonymous"] is False
    assert "google" in body["providers"]

    # Verify DB state
    db_session.expire_all()
    user = (
        db_session.query(User)
        .filter(User.firebase_uid == firebase_uid)
        .first()
    )
    assert user is not None
    assert user.is_anonymous is False

    assert db_session.query(UserProvider).count() == 1
    provider = db_session.query(UserProvider).first()
    assert provider.provider == OAuthProvider.google
    assert provider.provider_uid == google_sub


def test_data_preserved_after_link(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """Guest user → link Google → user_id (UUID) is unchanged (AC-F01-5).

    NOTE (DL-025): friends/photos tables do not exist yet (DL-018).
    This test verifies the core guarantee: the user's primary key UUID
    is preserved after linking, so all future FK references (friends,
    photos) will remain valid without any reassignment.

    TODO(F03/F05): Update fixture to INSERT 5 friends + 3 photos rows
    referencing ``user_id_before``, then assert those rows still
    reference the same ``user_id`` after POST /auth/link.

    Refs: AC-F01-5
    """
    firebase_uid, anon_token = _create_anonymous_user()
    resp = integration_client.post("/auth/session", headers=_auth(anon_token))
    assert resp.status_code == 200
    user_id_before = resp.json()["user_id"]

    # Link Google
    google_sub = f"google-preserve-{uuid.uuid4().hex[:8]}"
    _, linked_token = _sign_in_with_google(
        google_sub=google_sub, anon_id_token=anon_token
    )
    resp = integration_client.post("/auth/link", headers=_auth(linked_token))
    assert resp.status_code == 200
    user_id_after = resp.json()["user_id"]

    # Core guarantee: user UUID must not change after linking
    assert user_id_before == user_id_after

    # UserProvider is attached to the *original* user_id
    db_session.expire_all()
    provider = (
        db_session.query(UserProvider)
        .filter(
            UserProvider.provider == OAuthProvider.google,
            UserProvider.provider_uid == google_sub,
        )
        .first()
    )
    assert provider is not None
    assert str(provider.user_id) == user_id_after


def test_reinstall_guest_creates_new_uid(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """Two anonymous tokens → two independent rows; old row intact.

    Simulates an unlinked guest uninstalling and reinstalling the app.
    Each anonymous sign-in produces a new firebase_uid, and the backend
    must create a separate user record each time.

    Refs: AC-F01-7
    """
    # First install
    firebase_uid_a, token_a = _create_anonymous_user()
    resp = integration_client.post("/auth/session", headers=_auth(token_a))
    assert resp.status_code == 200
    user_id_a = resp.json()["user_id"]

    # Reinstall simulation: brand-new anonymous user
    firebase_uid_b, token_b = _create_anonymous_user()
    assert firebase_uid_b != firebase_uid_a  # emulator gives different UID

    resp = integration_client.post("/auth/session", headers=_auth(token_b))
    assert resp.status_code == 200
    user_id_b = resp.json()["user_id"]

    assert user_id_b != user_id_a
    db_session.expire_all()
    assert db_session.query(User).count() == 2

    # Old row still exists and is independent
    old_user = (
        db_session.query(User)
        .filter(User.firebase_uid == firebase_uid_a)
        .first()
    )
    assert old_user is not None
    assert str(old_user.id) == user_id_a


def test_reinstall_linked_restores_account(
    integration_client: TestClient,
    db_session: Session,
) -> None:
    """Linked user reinstalls → signs in with Google → original user_id.

    When a user has linked Google and reinstalls the app:
    1. Firebase returns the same firebase_uid (the linked account) when
       the user signs in with Google.
    2. Backend finds the existing user record by firebase_uid and returns
       the original user_id without creating a duplicate.

    Refs: AC-F01-8
    """
    # Step 1: create guest + link Google
    firebase_uid, anon_token = _create_anonymous_user()
    resp = integration_client.post("/auth/session", headers=_auth(anon_token))
    assert resp.status_code == 200
    original_user_id = resp.json()["user_id"]

    google_sub = f"google-restore-{uuid.uuid4().hex[:8]}"
    _, linked_token = _sign_in_with_google(
        google_sub=google_sub, anon_id_token=anon_token
    )
    resp = integration_client.post("/auth/link", headers=_auth(linked_token))
    assert resp.status_code == 200
    assert resp.json()["user_id"] == original_user_id

    # Step 2: simulate reinstall → sign in with the same Google account
    # Firebase emulator returns the same firebase_uid (the linked account)
    restored_uid, restore_token = _sign_in_with_google(google_sub=google_sub)
    assert restored_uid == firebase_uid  # same Firebase user, not new one

    # Step 3: session after reinstall must restore the original account
    resp = integration_client.post(
        "/auth/session", headers=_auth(restore_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == original_user_id
    assert body["firebase_uid"] == firebase_uid
    assert body["is_anonymous"] is False

    # No duplicate user created
    db_session.expire_all()
    assert db_session.query(User).count() == 1
