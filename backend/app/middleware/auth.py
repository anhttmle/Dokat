"""Firebase token verification middleware / dependency."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import firebase_admin.auth

_bearer = HTTPBearer(auto_error=False)


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI dependency that verifies the Firebase ID Token.

    Injects the decoded token payload into the route handler.
    Raises HTTP 401 on any validation failure.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "AUTH_TOKEN_MISSING", "message": "Token required"},
        )

    try:
        decoded = firebase_admin.auth.verify_id_token(credentials.credentials)
    except firebase_admin.auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTH_TOKEN_EXPIRED",
                "message": "Token has expired",
            },
        )
    except firebase_admin.auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTH_TOKEN_REVOKED",
                "message": "Token has been revoked",
            },
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTH_TOKEN_MISSING",
                "message": "Invalid token",
            },
        )

    return decoded
