"""Unit tests for upstream header stripping and injection (T-06, TDD)."""

import pytest

from app.proxy.headers import build_upstream_headers

_INTERNAL_JWT = "internal.jwt.token"
_TRACE_ID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture()
def original_headers() -> dict[str, str]:
    return {
        "authorization": "Bearer firebase-token",
        "host": "gateway.example.com",
        "connection": "keep-alive",
        "keep-alive": "timeout=5",
        "transfer-encoding": "chunked",
        "content-type": "application/json",
        "accept": "application/json",
    }


class TestStripHeaders:
    def test_strips_authorization(self, original_headers: dict[str, str]):
        result = build_upstream_headers(
            original_headers, _INTERNAL_JWT, _TRACE_ID
        )
        assert "authorization" not in result
        assert "Authorization" not in result

    def test_strips_host(self, original_headers: dict[str, str]):
        result = build_upstream_headers(
            original_headers, _INTERNAL_JWT, _TRACE_ID
        )
        assert "host" not in result
        assert "Host" not in result

    def test_strips_hop_by_hop_headers(self, original_headers: dict[str, str]):
        result = build_upstream_headers(
            original_headers, _INTERNAL_JWT, _TRACE_ID
        )
        for header in ("connection", "keep-alive", "transfer-encoding"):
            assert header not in result
            assert header.title() not in result


class TestAddHeaders:
    def test_adds_x_internal_token(self, original_headers: dict[str, str]):
        result = build_upstream_headers(
            original_headers, _INTERNAL_JWT, _TRACE_ID
        )
        assert result["X-Internal-Token"] == f"Bearer {_INTERNAL_JWT}"

    def test_adds_x_trace_id(self, original_headers: dict[str, str]):
        result = build_upstream_headers(
            original_headers, _INTERNAL_JWT, _TRACE_ID
        )
        assert result["X-Trace-ID"] == _TRACE_ID


class TestPassthroughHeaders:
    def test_passes_through_benign_headers(
        self, original_headers: dict[str, str]
    ):
        result = build_upstream_headers(
            original_headers, _INTERNAL_JWT, _TRACE_ID
        )
        assert result["content-type"] == "application/json"
        assert result["accept"] == "application/json"
