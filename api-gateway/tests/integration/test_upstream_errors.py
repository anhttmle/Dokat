"""Integration tests for upstream error handling — AC-05 (TDD).

Tests verify:
- Upstream timeout → 502 UPSTREAM_TIMEOUT, no stack trace in body.
- Connection refused → 503 UPSTREAM_UNAVAILABLE.
"""

import httpx
import respx
from fastapi.testclient import TestClient

from app.errors.codes import ErrorCode
from app.main import create_app


class TestUpstreamTimeout:
    @respx.mock
    def test_ac05_upstream_timeout_returns_502(self, mock_verify_id_token):
        """AC-05: upstream timeout → 502 UPSTREAM_TIMEOUT."""
        respx.get("http://pet-svc:8000/pets/123").mock(
            side_effect=httpx.TimeoutException("timed out")
        )

        with TestClient(create_app(), raise_server_exceptions=False) as client:
            resp = client.get(
                "/pets/123",
                headers={"Authorization": "Bearer firebase-token"},
            )

        assert resp.status_code == 502
        body = resp.json()
        assert body["error"]["code"] == ErrorCode.UPSTREAM_TIMEOUT
        assert "trace_id" in body["error"]

    @respx.mock
    def test_ac05_no_stack_trace_in_body(self, mock_verify_id_token):
        """AC-05: stack trace must not appear in response body."""
        respx.get("http://pet-svc:8000/pets/123").mock(
            side_effect=httpx.TimeoutException("timed out")
        )

        with TestClient(create_app(), raise_server_exceptions=False) as client:
            resp = client.get(
                "/pets/123",
                headers={"Authorization": "Bearer firebase-token"},
            )

        body_text = resp.text.lower()
        assert "traceback" not in body_text
        assert "stack" not in body_text


class TestUpstreamUnavailable:
    @respx.mock
    def test_connection_refused_returns_503(self, mock_verify_id_token):
        """Connection refused → 503 UPSTREAM_UNAVAILABLE."""
        respx.get("http://pet-svc:8000/pets/123").mock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with TestClient(create_app(), raise_server_exceptions=False) as client:
            resp = client.get(
                "/pets/123",
                headers={"Authorization": "Bearer firebase-token"},
            )

        assert resp.status_code == 503
        body = resp.json()
        assert body["error"]["code"] == ErrorCode.UPSTREAM_UNAVAILABLE
        assert "trace_id" in body["error"]


class TestUpstreamErrorNormalization:
    @respx.mock
    def test_upstream_404_json_keeps_status_and_adds_trace_id(
        self, mock_verify_id_token
    ):
        """Upstream 404 JSON error → status kept, trace_id added (T-09)."""
        respx.get("http://pet-svc:8000/pets/999").mock(
            return_value=httpx.Response(
                404,
                json={
                    "error": {
                        "code": "PET_NOT_FOUND",
                        "message": "Not found.",
                    }
                },
            )
        )

        with TestClient(create_app(), raise_server_exceptions=False) as client:
            resp = client.get(
                "/pets/999",
                headers={"Authorization": "Bearer firebase-token"},
            )

        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "PET_NOT_FOUND"
        assert body["error"]["message"] == "Not found."
        assert "trace_id" in body["error"]
        assert body["error"]["trace_id"]
