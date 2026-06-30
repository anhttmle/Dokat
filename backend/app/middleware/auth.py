"""Auth middleware supporting JWT and Firebase modes.

Chooses verification strategy based on ``settings.auth_mode``:

* ``"jwt"``      → verify internal JWT via :mod:`app.core.jwt_auth`
* ``"firebase"`` → verify Firebase ID Token via firebase-admin SDK

In both modes the verified identity is injected as
``request.state.firebase_uid`` so all downstream routers remain
unchanged (DL-F12-03).

Error mapping:
    - Missing/malformed header  → 401 AUTH_TOKEN_MISSING
    - Expired token             → 401 AUTH_TOKEN_EXPIRED
    - Revoked token (Firebase)  → 401 AUTH_TOKEN_REVOKED
    - Invalid token             → 401 AUTH_TOKEN_INVALID
    - Firebase SDK unavailable  → 503 AUTH_SERVICE_UNAVAILABLE
"""

import firebase_admin.auth
from fastapi import Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.jwt_auth import JWTAuthError, verify_token

_bearer = HTTPBearer(auto_error=False)

_BEARER_PREFIX = "Bearer "

# Paths that bypass auth — Swagger UI, OpenAPI schema, health check,
# and JWT token issuance endpoint.
_PUBLIC_PATHS = frozenset({
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/openapi.json",
    "/health",
    "/auth/token",
})


class AuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that verifies the Bearer token.

    Delegates to JWT or Firebase verification based on ``AUTH_MODE``.

    On success: sets ``request.state.firebase_uid`` and forwards the
    request to the next handler.

    On failure: returns a JSON error response immediately.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Verify token and inject firebase_uid, or return error."""
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith(_BEARER_PREFIX):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "AUTH_TOKEN_MISSING",
                    "message": "Token required",
                },
            )

        token = auth_header[len(_BEARER_PREFIX):]

        if settings.auth_mode == "jwt":
            return await self._verify_jwt(request, token, call_next)
        return await self._verify_firebase(request, token, call_next)

    async def _verify_jwt(
        self, request: Request, token: str, call_next
    ) -> Response:
        """Verify an internal JWT and inject the subject as firebase_uid."""
        try:
            sub = verify_token(token)
        except JWTAuthError as exc:
            if exc.reason == "expired":
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "AUTH_TOKEN_EXPIRED",
                        "message": "Token has expired",
                    },
                )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "AUTH_TOKEN_INVALID",
                    "message": "Token is invalid",
                },
            )

        request.state.firebase_uid = sub
        request.state.token_claims = {"sub": sub}
        return await call_next(request)

    async def _verify_firebase(
        self, request: Request, token: str, call_next
    ) -> Response:
        """Verify a Firebase ID Token and inject the uid as firebase_uid."""
        try:
            decoded = firebase_admin.auth.verify_id_token(token)
        except firebase_admin.auth.ExpiredIdTokenError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "AUTH_TOKEN_EXPIRED",
                    "message": "Token has expired",
                },
            )
        except firebase_admin.auth.RevokedIdTokenError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "AUTH_TOKEN_REVOKED",
                    "message": "Token has been revoked",
                },
            )
        except (
            firebase_admin.auth.InvalidIdTokenError,
            firebase_admin.auth.UserDisabledError,
            ValueError,
        ):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "AUTH_TOKEN_INVALID",
                    "message": "Token is invalid",
                },
            )
        except Exception:  # noqa: BLE001
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "AUTH_SERVICE_UNAVAILABLE",
                    "message": (
                        "Authentication service is temporarily unavailable"
                    ),
                },
            )

        request.state.firebase_uid = decoded["uid"]
        request.state.token_claims = decoded
        return await call_next(request)


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI dependency that verifies the Bearer token.

    Supports both JWT mode and Firebase mode.
    Raises HTTP 401 on any validation failure.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTH_TOKEN_MISSING",
                "message": "Token required",
            },
        )

    if settings.auth_mode == "jwt":
        try:
            sub = verify_token(credentials.credentials)
        except JWTAuthError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "AUTH_TOKEN_INVALID",
                    "message": "Token is invalid",
                },
            )
        return {"sub": sub, "uid": sub}

    try:
        decoded = firebase_admin.auth.verify_id_token(
            credentials.credentials
        )
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
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "AUTH_SERVICE_UNAVAILABLE",
                "message": (
                    "Authentication service is temporarily unavailable"
                ),
            },
        )

    return decoded
