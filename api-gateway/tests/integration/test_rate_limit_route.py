"""Integration tests for per-route rate limiting — AC-10 (TDD)."""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.errors.codes import ErrorCode
from app.main import create_app

_AUTH_HEADERS = {"Authorization": "Bearer firebase-token"}


@pytest.fixture()
def client_with_redis(mock_verify_id_token):  # noqa: ANN001
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        yield client


class TestRateLimitPerRoute:
    @respx.mock
    def test_ac10_capture_limit_does_not_block_other_routes(
        self, client_with_redis: TestClient
    ):
        """AC-10: capture limit 20/min; /pets still works for same user."""
        respx.post("http://capture-svc:8000/capture/foo").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        respx.get("http://pet-svc:8000/pets/123").mock(
            return_value=httpx.Response(200, json={"id": 123})
        )

        client = client_with_redis
        for _ in range(20):
            resp = client.post("/capture/foo", headers=_AUTH_HEADERS)
            assert resp.status_code == 200

        resp = client.post("/capture/foo", headers=_AUTH_HEADERS)
        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == ErrorCode.RATE_LIMIT_EXCEEDED

        resp = client.get("/pets/123", headers=_AUTH_HEADERS)
        assert resp.status_code == 200
