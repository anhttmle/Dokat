"""Integration tests for Trace ID middleware (TDD).

Covers FR-04.2 and AC-09:
- No X-Trace-ID header   → gateway generates a new UUID v4.
- Valid UUID v4 header   → gateway keeps it unchanged.
- Invalid header value   → gateway replaces it with a new UUID v4.
- Error response         → contains the same trace_id as the request.
"""

import re

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.errors.codes import ErrorCode
from app.errors.handlers import GatewayError, register_exception_handlers
from app.middleware.trace import TraceMiddleware

UUID_V4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"


def _build_app() -> FastAPI:
    """Minimal app: trace middleware + one echo route + one crashing route."""
    app = FastAPI()
    app.add_middleware(TraceMiddleware)
    register_exception_handlers(app)

    @app.get("/echo-trace")
    async def echo_trace(request: Request):  # noqa: RUF029
        """Return the trace_id set by the middleware."""
        return {"trace_id": request.state.trace_id}

    @app.get("/crash")
    async def crash():  # noqa: RUF029
        raise GatewayError(
            code=ErrorCode.INTERNAL_ERROR,
            message="boom",
            status_code=500,
        )

    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_build_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# AC-09 — trace_id generation / propagation
# ---------------------------------------------------------------------------


class TestTraceIdGeneration:
    def test_generates_uuid_when_header_absent(self, client: TestClient):
        body = client.get("/echo-trace").json()
        assert UUID_V4_RE.match(body["trace_id"]), (
            f"Expected UUID v4, got: {body['trace_id']}"
        )

    def test_each_request_gets_unique_trace_id(self, client: TestClient):
        t1 = client.get("/echo-trace").json()["trace_id"]
        t2 = client.get("/echo-trace").json()["trace_id"]
        assert t1 != t2

    def test_keeps_valid_uuid_from_client(self, client: TestClient):
        body = client.get(
            "/echo-trace", headers={"X-Trace-ID": VALID_UUID}
        ).json()
        assert body["trace_id"] == VALID_UUID

    def test_replaces_invalid_header_with_new_uuid(self, client: TestClient):
        body = client.get(
            "/echo-trace", headers={"X-Trace-ID": "not-a-uuid"}
        ).json()
        assert body["trace_id"] != "not-a-uuid"
        assert UUID_V4_RE.match(body["trace_id"])

    def test_replaces_empty_header_with_new_uuid(self, client: TestClient):
        body = client.get("/echo-trace", headers={"X-Trace-ID": ""}).json()
        assert UUID_V4_RE.match(body["trace_id"])


class TestTraceIdInErrorResponse:
    """AC-09: trace_id must appear in error response body."""

    def test_error_response_contains_trace_id(self, client: TestClient):
        body = client.get("/crash", headers={"X-Trace-ID": VALID_UUID}).json()
        assert body["error"]["trace_id"] == VALID_UUID

    def test_generated_trace_id_in_error_response(self, client: TestClient):
        body = client.get("/crash").json()
        assert UUID_V4_RE.match(body["error"]["trace_id"])
