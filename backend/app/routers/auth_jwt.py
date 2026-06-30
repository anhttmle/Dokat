"""JWT auth router: POST /auth/token (standalone mode only).

Registered by ``app/main.py`` only when ``AUTH_MODE=jwt``.

Refs: Design §3, AC-F12-2, DL-F12-06
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.jwt_auth import create_token
from app.routers.auth import get_db
from app.services.user_service import get_or_create_user

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenRequest(BaseModel):
    """Request body for POST /auth/token."""

    device_id: str


class TokenResponse(BaseModel):
    """Response body for POST /auth/token."""

    access_token: str
    user_id: uuid.UUID
    is_anonymous: bool


@router.post("/token", response_model=TokenResponse)
def issue_token(
    body: TokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Issue a JWT for an anonymous device session.

    Creates a user record on first call; returns the same JWT-issued
    identity on subsequent calls with the same ``device_id``.

    Args:
        body: ``TokenRequest`` with a non-empty ``device_id``.
        db: Injected sync DB session.

    Returns:
        ``TokenResponse`` with ``access_token``, ``user_id``,
        ``is_anonymous=True``.

    Raises:
        HTTP 422: If ``device_id`` is an empty string.
    """
    if not body.device_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "DEVICE_ID_REQUIRED",
                "message": "device_id must not be empty",
            },
        )

    user = get_or_create_user(db, body.device_id)
    token = create_token(body.device_id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        is_anonymous=user.is_anonymous,
    )
