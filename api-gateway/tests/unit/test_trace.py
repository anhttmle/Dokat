"""Unit tests for UUID validation helper in trace middleware (TDD).

Covers the pure logic: is a given string a valid UUID v4?
"""

from app.middleware.trace import is_valid_uuid_v4


class TestIsValidUuidV4:
    """is_valid_uuid_v4() must accept only well-formed UUID v4 strings."""

    # ------------------------------------------------------------------ valid

    def test_valid_uuid_v4_lowercase(self):
        assert is_valid_uuid_v4("550e8400-e29b-41d4-a716-446655440000") is True

    def test_valid_uuid_v4_uppercase(self):
        assert is_valid_uuid_v4("550E8400-E29B-41D4-A716-446655440000") is True

    def test_valid_uuid_v4_mixed_case(self):
        assert is_valid_uuid_v4("A987FBC9-4BED-4079-9f07-9A6CEFBE0A84") is True

    # ----------------------------------------------------------------- invalid

    def test_empty_string_is_invalid(self):
        assert is_valid_uuid_v4("") is False

    def test_none_is_invalid(self):
        assert is_valid_uuid_v4(None) is False  # type: ignore[arg-type]

    def test_plain_string_is_invalid(self):
        assert is_valid_uuid_v4("not-a-uuid") is False

    def test_uuid_missing_hyphens_is_invalid(self):
        assert is_valid_uuid_v4("550e8400e29b41d4a716446655440000") is False

    def test_uuid_wrong_length_is_invalid(self):
        assert is_valid_uuid_v4("550e8400-e29b-41d4-a716") is False

    def test_integer_is_invalid(self):
        assert is_valid_uuid_v4(12345) is False  # type: ignore[arg-type]

    def test_uuid_v1_format_still_validates(self):
        """We validate format, not version bits — keep behaviour simple."""
        assert is_valid_uuid_v4("6ba7b810-9dad-11d1-80b4-00c04fd430c8") is True
