"""Unit tests for upstream error normalization (T-09, TDD)."""

import json

from app.errors.codes import ErrorCode
from app.errors.normalizer import normalize_upstream_response

_TRACE_ID = "550e8400-e29b-41d4-a716-446655440000"
_HEADERS = {"x-custom": "value"}


class TestPassthrough:
    def test_2xx_passthrough_unchanged(self):
        body = b'{"id": 123}'
        status, out_body, out_headers = normalize_upstream_response(
            200, body, _HEADERS, _TRACE_ID
        )

        assert status == 200
        assert out_body == body
        assert out_headers == _HEADERS

    def test_3xx_passthrough_unchanged(self):
        body = b""
        status, out_body, out_headers = normalize_upstream_response(
            301, body, _HEADERS, _TRACE_ID
        )

        assert status == 301
        assert out_body == body
        assert out_headers == _HEADERS


class TestValidUpstreamError:
    def test_adds_trace_id_to_valid_error_schema(self):
        body = json.dumps(
            {
                "error": {
                    "code": "PET_NOT_FOUND",
                    "message": "Pet does not exist.",
                }
            }
        ).encode()

        status, out_body, out_headers = normalize_upstream_response(
            404, body, _HEADERS, _TRACE_ID
        )

        assert status == 404
        data = json.loads(out_body)
        assert data["error"]["code"] == "PET_NOT_FOUND"
        assert data["error"]["message"] == "Pet does not exist."
        assert data["error"]["trace_id"] == _TRACE_ID
        assert out_headers["content-type"] == "application/json"
        assert out_headers["x-custom"] == "value"


class TestInvalidUpstreamError:
    def test_invalid_json_wraps_upstream_error(self):
        status, out_body, out_headers = normalize_upstream_response(
            500, b"not json", _HEADERS, _TRACE_ID
        )

        assert status == 500
        data = json.loads(out_body)
        assert data["error"]["code"] == ErrorCode.UPSTREAM_ERROR
        assert data["error"]["trace_id"] == _TRACE_ID
        assert out_headers["content-type"] == "application/json"

    def test_non_json_bytes_wraps_upstream_error(self):
        status, out_body, _ = normalize_upstream_response(
            502, b"\xff\xfe invalid", _HEADERS, _TRACE_ID
        )

        assert status == 502
        data = json.loads(out_body)
        assert data["error"]["code"] == ErrorCode.UPSTREAM_ERROR

    def test_wrong_schema_wraps_upstream_error(self):
        body = json.dumps({"detail": "not found"}).encode()

        status, out_body, _ = normalize_upstream_response(
            404, body, _HEADERS, _TRACE_ID
        )

        assert status == 404
        data = json.loads(out_body)
        assert data["error"]["code"] == ErrorCode.UPSTREAM_ERROR
        assert data["error"]["trace_id"] == _TRACE_ID

    def test_fastapi_style_body_wraps_upstream_error(self):
        body = json.dumps({"detail": "Validation error"}).encode()

        status, out_body, out_headers = normalize_upstream_response(
            422, body, _HEADERS, _TRACE_ID
        )

        assert status == 422
        data = json.loads(out_body)
        assert data["error"]["code"] == ErrorCode.UPSTREAM_ERROR
        assert out_headers["content-type"] == "application/json"
