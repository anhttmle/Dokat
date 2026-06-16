"""Integration tests for per-user rate limiting — AC-03 (TDD)."""

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


class TestRateLimitPerUser:
    @respx.mock
    def test_ac03_201st_request_returns_429(
        self, client_with_redis: TestClient
    ):
        """AC-03: 201 requests in 1 minute → 429 + Retry-After."""
        respx.get("http://pet-svc:8000/pets/123").mock(
            return_value=httpx.Response(200, json={"id": 123})
        )

        client = client_with_redis
        for _ in range(200):
            resp = client.get("/pets/123", headers=_AUTH_HEADERS)
            assert resp.status_code == 200

        resp = client.get("/pets/123", headers=_AUTH_HEADERS)
        assert resp.status_code == 429
        assert int(resp.headers["retry-after"]) > 0
        body = resp.json()
        assert body["error"]["code"] == ErrorCode.RATE_LIMIT_EXCEEDED
