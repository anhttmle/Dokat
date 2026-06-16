"""Normalize upstream 4xx/5xx responses to gateway error format (FR-05.2)."""

import json

from app.errors.codes import ErrorCode
from app.errors.handlers import error_response

_GENERIC_MESSAGE = "An upstream error occurred."


def _json_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return headers with content-type set to application/json."""
    result = dict(headers)
    result["content-type"] = "application/json"
    return result


def _wrap_error(
    status_code: int,
    headers: dict[str, str],
    trace_id: str,
) -> tuple[int, bytes, dict[str, str]]:
    """Wrap invalid upstream error body in standard gateway format."""
    body = json.dumps(
        error_response(ErrorCode.UPSTREAM_ERROR, _GENERIC_MESSAGE, trace_id)
    ).encode()
    return status_code, body, _json_headers(headers)


def _is_valid_upstream_error(data: object) -> bool:
    """Return True when data matches upstream error schema (D-06)."""
    if not isinstance(data, dict):
        return False
    error = data.get("error")
    if not isinstance(error, dict):
        return False
    return isinstance(error.get("code"), str) and isinstance(
        error.get("message"), str
    )


def normalize_upstream_response(
    status_code: int,
    body: bytes,
    headers: dict[str, str],
    trace_id: str,
) -> tuple[int, bytes, dict[str, str]]:
    """Normalize upstream response body for 4xx/5xx errors.

    2xx/3xx responses are returned unchanged. Valid upstream error JSON
    gets ``trace_id`` injected. Invalid JSON or schema is wrapped as
    ``UPSTREAM_ERROR``.

    Args:
        status_code: HTTP status from upstream.
        body: Raw response body bytes.
        headers: Response headers (hop-by-hop already stripped).
        trace_id: Request trace identifier.

    Returns:
        Tuple of (status_code, body_bytes, headers).
    """
    if status_code < 400:
        return status_code, body, headers

    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return _wrap_error(status_code, headers, trace_id)

    if not _is_valid_upstream_error(data):
        return _wrap_error(status_code, headers, trace_id)

    error = data["error"]
    error["trace_id"] = trace_id
    new_body = json.dumps(data).encode()
    return status_code, new_body, _json_headers(headers)
