"""Storage helpers: presigned upload URLs and public URL building.

Supports two backends selected via ``STORAGE_BACKEND``:
* ``"s3"``    — AWS S3 + CloudFront CDN (original behaviour)
* ``"minio"`` — self-hosted MinIO (S3-compatible, no external deps)

Refs: Design §3.3, §3.8, §4.2; DL-F02-04, DL-F12-04, DL-F12-05
"""

import time

import boto3
from botocore.config import Config

from app.core.config import settings
from app.schemas.profile import PresignedUrlResponse

ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)

_CONTENT_TYPE_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

_S3_CONFIG = Config(signature_version="s3v4")


class InvalidContentTypeError(Exception):
    """Raised when an unsupported upload content type is requested."""


def _get_s3_client():
    """Return a boto3 S3 client configured for the active storage backend.

    For MinIO, ``endpoint_url`` is set so boto3 routes requests to the
    local MinIO server instead of AWS (DL-F12-04).
    """
    kwargs: dict = {
        "region_name": settings.aws_region,
        "config": _S3_CONFIG,
    }
    if settings.storage_backend == "minio":
        kwargs["endpoint_url"] = settings.minio_endpoint_url
    return boto3.client("s3", **kwargs)


def build_cdn_url(object_key: str) -> str:
    """Return the public URL for the given object key.

    * MinIO mode: ``{minio_endpoint_url}/{s3_bucket}/{object_key}``
    * S3 mode:    ``{cdn_base_url}/{object_key}`` (CloudFront)

    Args:
        object_key: S3/MinIO object key (no leading slash).

    Returns:
        Full public URL string.
    """
    if settings.storage_backend == "minio":
        return (
            f"{settings.minio_endpoint_url}"
            f"/{settings.s3_bucket}/{object_key}"
        )
    return f"{settings.cdn_base_url}/{object_key}"


def generate_upload_url(
    user_id: str,
    prefix: str,
    content_type: str,
    expires_in: int = 300,
) -> PresignedUrlResponse:
    """Generate a presigned PUT URL with a user-scoped object key.

    The object key is built as ``{prefix}/{user_id}/{timestamp}.{ext}``
    so that all uploads for a user are grouped under their ID (DL-F02-04).

    Args:
        user_id: Authenticated user identifier (Firebase UID or device_id).
        prefix: Key prefix, e.g. ``"avatars/users"`` or ``"posts"``.
        content_type: Image MIME type; must be in ``ALLOWED_CONTENT_TYPES``.
        expires_in: Presigned URL lifetime in seconds (default 300).

    Returns:
        Populated ``PresignedUrlResponse``.

    Raises:
        InvalidContentTypeError: If ``content_type`` is not allowed.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidContentTypeError(content_type)

    ext = _CONTENT_TYPE_TO_EXT[content_type]
    timestamp = int(time.time())
    object_key = f"{prefix}/{user_id}/{timestamp}.{ext}"

    client = _get_s3_client()
    upload_url: str = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
    cdn_url = build_cdn_url(object_key)
    return PresignedUrlResponse(
        upload_url=upload_url,
        object_key=object_key,
        cdn_url=cdn_url,
        expires_in=expires_in,
    )


def generate_presigned_url(
    object_key: str,
    content_type: str,
    expires_in: int = 300,
) -> PresignedUrlResponse:
    """Generate a presigned PUT URL for an explicit object key.

    Args:
        object_key: Target object key.
        content_type: Image MIME type; must be in ``ALLOWED_CONTENT_TYPES``.
        expires_in: URL lifetime in seconds.

    Returns:
        Populated ``PresignedUrlResponse``.

    Raises:
        InvalidContentTypeError: If ``content_type`` is unsupported.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidContentTypeError(content_type)

    client = _get_s3_client()
    upload_url: str = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
    cdn_url = build_cdn_url(object_key)
    return PresignedUrlResponse(
        upload_url=upload_url,
        object_key=object_key,
        cdn_url=cdn_url,
        expires_in=expires_in,
    )
