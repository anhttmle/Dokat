"""S3 storage helpers: presigned upload URLs and CDN URL building.

Refs: Design §3.3, §3.8, §4.2; DL-F02-04
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


def build_cdn_url(object_key: str) -> str:
    """Return the public CloudFront URL for an S3 object key.

    Args:
        object_key: S3 object key (no leading slash).

    Returns:
        Full CDN URL string.
    """
    return f"{settings.cdn_base_url}/{object_key}"


def generate_upload_url(
    user_id: str,
    prefix: str,
    content_type: str,
    expires_in: int = 300,
) -> PresignedUrlResponse:
    """Generate a presigned S3 PUT URL with a user-scoped object key.

    The object key is built as ``{prefix}/{user_id}/{timestamp}.{ext}``
    so that all uploads for a user are grouped under their ID (DL-F02-04).

    Args:
        user_id: Firebase UID of the requesting user.
        prefix: S3 key prefix, e.g. ``"avatars/users"`` or
            ``"avatars/pets"``.
        content_type: Image MIME type; must be in
            ``ALLOWED_CONTENT_TYPES``.
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

    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        config=_S3_CONFIG,
    )
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
    """Generate a presigned S3 PUT URL for an explicit object key.

    Args:
        object_key: Target S3 object key.
        content_type: Image MIME type; must be in
            ``ALLOWED_CONTENT_TYPES``.
        expires_in: URL lifetime in seconds.

    Returns:
        Populated ``PresignedUrlResponse``.

    Raises:
        InvalidContentTypeError: If ``content_type`` is unsupported.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidContentTypeError(content_type)

    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        config=_S3_CONFIG,
    )
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
