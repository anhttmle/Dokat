"""Integration tests for routing — 404 on unknown path (TDD).

Full happy-path routing (AC-01) is tested in T-06 after the proxy
forwarder is implemented. This file covers FR-01.4 only.
"""

import pytest
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
