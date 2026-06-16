"""Integration tests for routing — 404 on unknown path and AC-01 (TDD).

Covers FR-01.4 (route not found) and AC-01 (happy-path proxy forwarding).
"""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


class TestRouteNotFound:
    def test_unknown_path_returns_404(self, client: TestClient):
        resp = client.get("/does-not-exist/foo")
        assert resp.status_code == 404

    def test_404_has_standard_error_schema(self, client: TestClient):
        body = client.get("/no-such-route").json()
        assert "error" in body
        assert set(body["error"].keys()) == {"code", "message", "trace_id"}

    def test_404_code_is_route_not_found(self, client: TestClient):
        body = client.get("/totally/unknown").json()
        assert body["error"]["code"] == "ROUTE_NOT_FOUND"

    def test_root_path_returns_404(self, client: TestClient):
        resp = client.get("/")
        assert resp.status_code == 404

    def test_partial_prefix_without_slash_returns_404(
        self, client: TestClient
    ):
        """'/pet' is not registered; only '/pets/...' is."""
        resp = client.get("/pet")
        assert resp.status_code == 404


class TestProxyHappyPath:
    @respx.mock
    def test_ac01_upstream_receives_x_internal_token(
        self, mock_verify_id_token
    ):
        """AC-01: valid token → upstream receives X-Internal-Token."""
        respx.get("http://pet-svc:8000/pets/123").mock(
            return_value=httpx.Response(200, json={"id": 123})
        )

        with TestClient(create_app(), raise_server_exceptions=False) as c:
            resp = c.get(
                "/pets/123",
                headers={"Authorization": "Bearer firebase-token"},
            )

        assert resp.status_code == 200
        assert resp.json() == {"id": 123}
        upstream_req = respx.calls[0].request
        assert upstream_req.headers.get("x-internal-token") is not None
        assert upstream_req.headers.get("authorization") is None
