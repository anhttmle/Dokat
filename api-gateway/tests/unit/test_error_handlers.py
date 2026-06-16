"""Unit tests for error schema helper and error codes (TDD).

Covers FR-05.1 (standard error schema) and FR-05.5 (no stack trace in body).
"""

import pytest

from app.errors.codes import ErrorCode
from app.errors.handlers import error_response


class TestErrorCodes:
    """All required error codes must exist in the enum."""

    _REQUIRED = [
        "UNAUTHORIZED",
        "ROUTE_NOT_FOUND",
        "RATE_LIMIT_EXCEEDED",
        "UPSTREAM_TIMEOUT",
        "UPSTREAM_UNAVAILABLE",
        "INTERNAL_ERROR",
        "UPSTREAM_ERROR",
    ]

    def test_all_codes_exist(self):
        for name in self._REQUIRED:
            assert hasattr(ErrorCode, name), f"ErrorCode missing: {name}"

    def test_codes_are_strings(self):
        for name in self._REQUIRED:
            code = getattr(ErrorCode, name)
            assert isinstance(code, str), f"ErrorCode.{name} is not a string"

    def test_code_value_matches_name(self):
        """String value must equal the enum member name."""
        for name in self._REQUIRED:
            code = getattr(ErrorCode, name)
            assert str(code) == name, (
                f"ErrorCode.{name} value mismatch: got '{code}'"
            )


class TestErrorResponseSchema:
    """error_response() must return the canonical FR-05.1 JSON structure."""

    def test_top_level_key_is_error(self):
        body = error_response(ErrorCode.INTERNAL_ERROR, "oops", "t1")
        assert set(body.keys()) == {"error"}

    def test_error_contains_required_keys(self):
        body = error_response(ErrorCode.INTERNAL_ERROR, "oops", "t1")
        assert set(body["error"].keys()) == {"code", "message", "trace_id"}

    def test_code_is_string(self):
        body = error_response(ErrorCode.UNAUTHORIZED, "bad token", "t2")
        assert body["error"]["code"] == "UNAUTHORIZED"

    def test_message_is_preserved(self):
        msg = "Too many requests. Retry after 30 seconds."
        body = error_response(ErrorCode.RATE_LIMIT_EXCEEDED, msg, "t3")
        assert body["error"]["message"] == msg

    def test_trace_id_is_preserved(self):
        tid = "550e8400-e29b-41d4-a716-446655440000"
        body = error_response(ErrorCode.ROUTE_NOT_FOUND, "not found", tid)
        assert body["error"]["trace_id"] == tid

    def test_no_stack_trace_in_body(self):
        """FR-05.5: response dict must not contain any stack trace text."""
        body = error_response(ErrorCode.INTERNAL_ERROR, "Internal error", "t4")
        body_str = str(body)
        assert "Traceback" not in body_str
        assert 'File "' not in body_str

    @pytest.mark.parametrize(
        "code",
        [
            ErrorCode.UNAUTHORIZED,
            ErrorCode.ROUTE_NOT_FOUND,
            ErrorCode.RATE_LIMIT_EXCEEDED,
            ErrorCode.UPSTREAM_TIMEOUT,
            ErrorCode.UPSTREAM_UNAVAILABLE,
            ErrorCode.UPSTREAM_ERROR,
        ],
    )
    def test_all_codes_produce_valid_schema(self, code):
        body = error_response(code, "some message", "trace-abc")
        assert body["error"]["code"] == str(code)
