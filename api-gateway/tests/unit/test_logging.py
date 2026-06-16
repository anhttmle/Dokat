"""Unit tests for access logging middleware (T-07, TDD)."""

import json
import logging
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.auth.dependency import AuthContext
from app.middleware.logging import (
    AccessLoggingMiddleware,
    _build_log_entry,
)
from app.routing.registry import RouteConfig

_FIREBASE_TOKEN = "firebase-secret-token-value"
_INTERNAL_JWT = "internal.jwt.secret.payload"
_TRACE_ID = "550e8400-e29b-41d4-a716-446655440000"

_REQUIRED_KEYS = frozenset(
    {
        "trace_id",
        "timestamp",
        "method",
        "path",
        "status_code",
        "latency_ms",
        "upstream_latency_ms",
        "user_id",
        "client_ip",
        "upstream",
        "route_id",
    }
)


@pytest.fixture()
def mock_request() -> MagicMock:
    """Minimal request mock with auth and route state."""
    request = MagicMock()
    request.method = "GET"
    request.url.path = "/pets/123"
    request.headers = {"authorization": f"Bearer {_FIREBASE_TOKEN}"}
    request.client = MagicMock()
    request.client.host = "203.0.113.1"
    request.state.trace_id = _TRACE_ID
    request.state.auth = AuthContext(
        uid="test-user-123",
        email="test@example.com",
        auth_provider="google.com",
        internal_jwt=_INTERNAL_JWT,
    )
    request.state.route = RouteConfig(
        prefix="/pets",
        route_id="pets",
        upstream_url="http://pet-svc:8000",
    )
    request.state.upstream_latency_ms = 38.5
    return request


class TestBuildLogEntrySchema:
    def test_contains_required_keys(self, mock_request: MagicMock):
        entry = _build_log_entry(mock_request, 200, 45.123)
        assert set(entry.keys()) == _REQUIRED_KEYS

    def test_field_values(self, mock_request: MagicMock):
        entry = _build_log_entry(mock_request, 200, 45.123)

        assert entry["trace_id"] == _TRACE_ID
        assert entry["method"] == "GET"
        assert entry["path"] == "/pets/123"
        assert entry["status_code"] == 200
        assert entry["latency_ms"] == 45.12
        assert entry["upstream_latency_ms"] == 38.5
        assert entry["user_id"] == "test-user-123"
        assert entry["client_ip"] == "203.0.113.1"
        assert entry["upstream"] == "http://pet-svc:8000"
        assert entry["route_id"] == "pets"
        assert entry["timestamp"].endswith("Z")

    def test_null_safe_when_state_not_set(self):
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/health"
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.state = MagicMock(spec=[])

        entry = _build_log_entry(request, 200, 1.0)

        assert entry["user_id"] is None
        assert entry["upstream"] is None
        assert entry["route_id"] is None
        assert entry["upstream_latency_ms"] is None


class TestAc08NoSecretsInLog:
    def test_log_entry_does_not_contain_firebase_token(
        self, mock_request: MagicMock
    ):
        entry = _build_log_entry(mock_request, 200, 45.0)
        serialized = json.dumps(entry)

        assert _FIREBASE_TOKEN not in serialized
        assert "Bearer" not in serialized

    def test_log_entry_does_not_contain_internal_jwt(
        self, mock_request: MagicMock
    ):
        entry = _build_log_entry(mock_request, 200, 45.0)
        serialized = json.dumps(entry)

        assert _INTERNAL_JWT not in serialized

    def test_log_entry_does_not_contain_authorization_header(
        self, mock_request: MagicMock
    ):
        entry = _build_log_entry(mock_request, 200, 45.0)

        assert "authorization" not in entry
        assert "Authorization" not in entry


class TestAccessLoggingMiddlewareLevel:
    @pytest.fixture()
    def logging_app(self) -> FastAPI:
        app = FastAPI()
        app.add_middleware(AccessLoggingMiddleware)

        @app.get("/ok")
        async def ok() -> dict:  # noqa: RUF029
            return {"status": "ok"}

        @app.get("/error")
        async def error():  # noqa: RUF029
            return JSONResponse(status_code=500, content={"error": "boom"})

        return app

    def test_2xx_logs_at_info(self, logging_app: FastAPI, caplog):
        with caplog.at_level(logging.INFO):
            with TestClient(logging_app, raise_server_exceptions=False) as c:
                c.get("/ok")

        info_records = [
            r
            for r in caplog.records
            if r.name == "app.middleware.logging" and r.levelno == logging.INFO
        ]
        assert len(info_records) == 1
        entry = json.loads(info_records[0].message)
        assert entry["status_code"] == 200

    def test_5xx_logs_at_error(self, logging_app: FastAPI, caplog):
        with caplog.at_level(logging.ERROR):
            with TestClient(logging_app, raise_server_exceptions=False) as c:
                c.get("/error")

        error_records = [
            r
            for r in caplog.records
            if r.name == "app.middleware.logging"
            and r.levelno == logging.ERROR
        ]
        assert len(error_records) == 1
        entry = json.loads(error_records[0].message)
        assert entry["status_code"] == 500
