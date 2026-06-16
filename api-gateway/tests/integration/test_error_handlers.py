"""Integration tests for global exception handlers (TDD).

Verifies that:
- Uncaught exceptions → HTTP 500 with standard error schema (FR-05.1).
- Stack trace does NOT appear in the response body (FR-05.5).
- GatewayError is rendered with the correct status code and schema.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors.codes import ErrorCode
from app.errors.handlers import GatewayError, register_exception_handlers

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_with_handlers() -> FastAPI:
    """Minimal FastAPI app with exception handlers registered."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/crash")
    async def crash():  # noqa: RUF029
        raise RuntimeError("unexpected boom")

    @app.get("/gateway-error")
    async def gateway_err():  # noqa: RUF029
        raise GatewayError(
            code=ErrorCode.UNAUTHORIZED,
            message="Firebase token expired.",
            status_code=401,
        )

    return app


@pytest.fixture()
def client(app_with_handlers: FastAPI) -> TestClient:
    return TestClient(app_with_handlers, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Uncaught exception → 500
# ---------------------------------------------------------------------------


class TestUnhandledException:
    def test_status_is_500(self, client: TestClient):
        resp = client.get("/crash")
        assert resp.status_code == 500

    def test_body_has_standard_schema(self, client: TestClient):
        body = client.get("/crash").json()
        assert "error" in body
        assert set(body["error"].keys()) == {"code", "message", "trace_id"}

    def test_code_is_internal_error(self, client: TestClient):
        body = client.get("/crash").json()
        assert body["error"]["code"] == "INTERNAL_ERROR"

    def test_no_stack_trace_in_body(self, client: TestClient):
        """FR-05.5: RuntimeError detail must NOT leak into the response."""
        text = client.get("/crash").text
        assert "Traceback" not in text
        assert "unexpected boom" not in text
        assert "RuntimeError" not in text

    def test_trace_id_key_present(self, client: TestClient):
        body = client.get("/crash").json()
        assert "trace_id" in body["error"]


# ---------------------------------------------------------------------------
# GatewayError → correct status + schema
# ---------------------------------------------------------------------------


class TestGatewayError:
    def test_status_code_is_propagated(self, client: TestClient):
        resp = client.get("/gateway-error")
        assert resp.status_code == 401

    def test_body_has_standard_schema(self, client: TestClient):
        body = client.get("/gateway-error").json()
        assert set(body["error"].keys()) == {"code", "message", "trace_id"}

    def test_code_is_unauthorized(self, client: TestClient):
        body = client.get("/gateway-error").json()
        assert body["error"]["code"] == "UNAUTHORIZED"

    def test_message_is_propagated(self, client: TestClient):
        body = client.get("/gateway-error").json()
        assert body["error"]["message"] == "Firebase token expired."
