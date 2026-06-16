"""Gateway error code enum.

Each value matches its member name so that the wire format is stable and
readable (e.g. ``"UNAUTHORIZED"`` rather than an integer).
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    """Canonical error codes returned in gateway error responses (FR-05.1)."""

    UNAUTHORIZED = "UNAUTHORIZED"
    ROUTE_NOT_FOUND = "ROUTE_NOT_FOUND"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
