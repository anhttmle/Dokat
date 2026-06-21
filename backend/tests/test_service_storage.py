"""Unit tests for storage_service presigned URL generation.

Uses moto to mock S3 so no real AWS calls are made. Written TDD-style;
tests are expected to FAIL until storage_service is implemented in
later F02 tasks.

Refs: Design §3.3, §3.8, §4.2, §6.2; DL-F02-04
"""

import boto3
import pytest
from moto import mock_aws

from app.services import storage_service

_TEST_CDN = "https://cdn.pawsnap.app"
_TEST_BUCKET = "pawsnap"


@pytest.fixture()
def s3_bucket():
    """Create a mocked S3 bucket for the duration of a test."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_TEST_BUCKET)
        yield client


def test_generate_presigned_url_returns_url(s3_bucket) -> None:
    """A valid content_type yields a presigned PUT URL and CDN URL."""
    result = storage_service.generate_presigned_url(
        object_key="avatars/users/abc/1.jpg",
        content_type="image/jpeg",
    )

    assert result.upload_url.startswith("http")
    assert result.object_key == "avatars/users/abc/1.jpg"
    assert result.cdn_url.startswith("http")
    assert result.expires_in == 300


def test_generate_presigned_url_invalid_content_type(s3_bucket) -> None:
    """An unsupported content_type raises InvalidContentTypeError."""
    with pytest.raises(storage_service.InvalidContentTypeError):
        storage_service.generate_presigned_url(
            object_key="avatars/users/abc/1.mp4",
            content_type="video/mp4",
        )


# ---------------------------------------------------------------------------
# Task 4.1 — 4 new tests (expected FAIL until task 4.2 is implemented)
# ---------------------------------------------------------------------------


def test_generate_owner_avatar_upload_url_returns_presigned_url(
    s3_bucket,
) -> None:
    """POST /profile/me/avatar/upload-url flow:
    generate_upload_url returns upload_url with X-Amz-Signature,
    cdn_url containing CDN_BASE_URL, and expires_in=300.
    """
    result = storage_service.generate_upload_url(
        user_id="owner-uid-abc",
        prefix="avatars/users",
        content_type="image/jpeg",
    )

    assert "X-Amz-Signature" in result.upload_url
    assert _TEST_CDN in result.cdn_url
    assert result.expires_in == 300


def test_generate_pet_avatar_upload_url_uses_user_id_in_key(
    s3_bucket,
) -> None:
    """POST /pets/avatar/upload-url flow:
    object_key for pet avatar includes user_id (DL-F02-04).
    """
    result = storage_service.generate_upload_url(
        user_id="pet-owner-uid",
        prefix="avatars/pets",
        content_type="image/jpeg",
    )

    assert "pet-owner-uid" in result.object_key


def test_invalid_content_type_returns_400() -> None:
    """video/mp4 raises InvalidContentTypeError (mapped to 400 in router)."""
    with pytest.raises(storage_service.InvalidContentTypeError):
        storage_service.generate_upload_url(
            user_id="some-uid",
            prefix="avatars/users",
            content_type="video/mp4",
        )


def test_cdn_url_built_from_object_key() -> None:
    """build_cdn_url returns CDN_BASE_URL + '/' + object_key."""
    object_key = "avatars/users/uid/ts.jpg"
    cdn_url = storage_service.build_cdn_url(object_key)
    assert cdn_url == f"{_TEST_CDN}/{object_key}"
