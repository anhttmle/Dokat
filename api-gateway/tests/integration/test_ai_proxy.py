"""Integration tests for AI route proxy — T-11 (TDD).

Covers FR-01.2 (Third-party AI), D-07:
- Valid Firebase token + POST /ai/analyze → upstream receives AI API Key.
- Upstream does NOT receive X-Internal-Token.
- Missing Firebase token → 401.
"""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.errors.codes import ErrorCode
from app.main import create_app

_AI_API_KEY = "test-ai-api-key-secret"
_AI_UPSTREAM_URL = "http://ai-provider.example.com/ai/analyze"


@pytest.fixture()
def ai_api_key(monkeypatch):
    """Set AI_API_KEY for tests that forward to the AI provider."""
    monkeypatch.setenv("AI_API_KEY", _AI_API_KEY)


class TestAiProxyHappyPath:
    @respx.mock
    def test_upstream_receives_ai_api_key(
        self, mock_verify_id_token, ai_api_key
    ):
        """Valid Firebase token → upstream receives AI API Key."""
        respx.post(_AI_UPSTREAM_URL).mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )

        with TestClient(create_app(), raise_server_exceptions=False) as c:
            resp = c.post(
                "/ai/analyze",
                headers={"Authorization": "Bearer firebase-token"},
                json={"text": "hello"},
            )

        assert resp.status_code == 200
        upstream_req = respx.calls[0].request
        assert upstream_req.headers.get("authorization") == (
            f"Bearer {_AI_API_KEY}"
        )

    @respx.mock
    def test_upstream_does_not_receive_x_internal_token(
        self, mock_verify_id_token, ai_api_key
    ):
        """AI upstream must not receive X-Internal-Token (D-07)."""
        respx.post(_AI_UPSTREAM_URL).mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )

        with TestClient(create_app(), raise_server_exceptions=False) as c:
            c.post(
                "/ai/analyze",
                headers={"Authorization": "Bearer firebase-token"},
                json={"text": "hello"},
            )

        upstream_req = respx.calls[0].request
        assert upstream_req.headers.get("x-internal-token") is None


class TestAiProxyAuth:
    def test_missing_firebase_token_returns_401(self):
        """Missing Authorization header on /ai/* → 401 UNAUTHORIZED."""
        with TestClient(create_app(), raise_server_exceptions=False) as c:
            resp = c.post("/ai/analyze", json={"text": "hello"})

        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == ErrorCode.UNAUTHORIZED
