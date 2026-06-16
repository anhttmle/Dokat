"""Integration tests for health check endpoint — AC-07 (TDD)."""

import httpx
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import _UPSTREAM_BASE_URLS


def _mock_all_upstream_health_up() -> None:
    for base_url in _UPSTREAM_BASE_URLS:
        respx.get(f"{base_url}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )


class TestHealthCheckAc07:
    @respx.mock
    def test_ac07_all_critical_up_returns_200(self):
        """AC-07: all critical upstreams up → 200 + upstream statuses."""
        _mock_all_upstream_health_up()

        with TestClient(create_app(), raise_server_exceptions=False) as client:
            resp = client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["gateway"] == "ok"
        assert "timestamp" in body
        assert "upstreams" in body
        assert body["upstreams"]["user-service"]["status"] == "up"
        assert body["upstreams"]["pet-service"]["status"] == "up"
        assert body["upstreams"]["onboarding-service"]["status"] == "up"

    @respx.mock
    def test_critical_upstream_down_returns_503(self):
        """User service down → HTTP 503."""
        _mock_all_upstream_health_up()
        respx.get("http://user-svc:8000/health").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with TestClient(create_app(), raise_server_exceptions=False) as client:
            resp = client.get("/health")

        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "unhealthy"
        assert body["upstreams"]["user-service"]["status"] == "down"

    @respx.mock
    def test_non_critical_down_returns_200_degraded(self):
        """Capture down but critical up → 200 degraded."""
        _mock_all_upstream_health_up()
        respx.get("http://capture-svc:8000/health").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with TestClient(create_app(), raise_server_exceptions=False) as client:
            resp = client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["upstreams"]["capture-service"]["status"] == "down"
        assert body["upstreams"]["user-service"]["status"] == "up"

    @respx.mock
    def test_no_authorization_required(self):
        """GET /health must not require Authorization header."""
        _mock_all_upstream_health_up()

        with TestClient(create_app(), raise_server_exceptions=False) as client:
            resp = client.get("/health")

        assert resp.status_code != 401
