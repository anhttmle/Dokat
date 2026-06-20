"""Shared fixtures for integration tests.

Prerequisites (must be running before ``make test-integration``):
  - Firebase Auth Emulator:
      firebase emulators:start --only auth
  - PostgreSQL test database accessible at TEST_DATABASE_URL

Environment variables:
  FIREBASE_AUTH_EMULATOR_HOST  Firebase emulator host (default: localhost:9099)
  FIREBASE_PROJECT_ID          Firebase project ID (default: demo-test)
  TEST_DATABASE_URL            PostgreSQL URL for the test database
                               (default: postgresql://postgres:postgres@
                                localhost:5432/me_test)

Note: The Admin SDK is initialised with ApplicationDefault credentials.
With FIREBASE_AUTH_EMULATOR_HOST set, verify_id_token talks to the
local emulator and never calls google.com, so the credential is never
actually used (lazy fetch). If your environment has no ADC configured,
set FIREBASE_CREDENTIALS_JSON (the same env var used by the app).
"""

import json
import os
from collections.abc import Generator

import firebase_admin
import pytest
from firebase_admin import credentials
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.models.user import Base
from app.routers.auth import get_db

EMULATOR_HOST = os.environ.get(
    "FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099"
)
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "demo-test")
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/me_test",
)


@pytest.fixture(scope="session", autouse=True)
def init_firebase_emulator() -> Generator[None, None, None]:
    """Initialise firebase_admin SDK pointing at the local emulator.

    With FIREBASE_AUTH_EMULATOR_HOST set the Admin SDK routes all
    auth.verify_id_token() calls to the emulator.  The credential is
    lazy and never fetched during emulator verification.
    """
    os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", EMULATOR_HOST)

    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_CREDENTIALS_JSON", "")
        if cred_json:
            cred: credentials.Base = credentials.Certificate(
                json.loads(cred_json)
            )
        else:
            cred = credentials.ApplicationDefault()

        firebase_admin.initialize_app(
            cred, {"projectId": FIREBASE_PROJECT_ID}
        )

    yield


@pytest.fixture(scope="module")
def pg_engine():
    """Create a module-scoped PostgreSQL engine and ensure tables exist.

    Uses NullPool so each connection is closed immediately—avoids
    "connection already used in another context" with cleanup statements.
    """
    engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(pg_engine) -> Generator[Session, None, None]:
    """Yield an isolated DB session; TRUNCATE all rows after each test."""
    factory = sessionmaker(bind=pg_engine)
    session = factory()
    yield session
    session.close()
    with pg_engine.connect() as conn:
        conn.execute(
            text("TRUNCATE TABLE user_providers, users CASCADE")
        )
        conn.commit()


@pytest.fixture()
def integration_client(db_session: Session):
    """TestClient with real firebase_admin (emulator) + real PostgreSQL."""
    from fastapi.testclient import TestClient

    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()
