"""Integration tests for per-IP rate limiting — AC-04 (TDD)."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client_with_redis():
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        yield client


class TestRateLimitPerIp:
    def test_ac04_31st_public_request_returns_429(
        self, client_with_redis: TestClient
    ):
        """AC-04: 31 requests/min to public endpoint → 429 + Retry-After."""
        client = client_with_redis
        for _ in range(30):
            resp = client.get("/health")
            assert resp.status_code == 200

        resp = client.get("/health")
        assert resp.status_code == 429
        assert int(resp.headers["retry-after"]) > 0
