"""Firebase token verification middleware and dependency."""

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

_bearer = HTTPBearer(auto_error=False)

_BEARER_PREFIX = "Bearer "

# Paths that bypass auth — Swagger UI, OpenAPI schema, health check.
_PUBLIC_PATHS = frozenset({
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/openapi.json",
    "/health",
})


class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that verifies the Firebase ID Token.

    Applied via ``app.add_middleware(FirebaseAuthMiddleware)``.

    On success: sets ``request.state.firebase_uid`` and forwards the
    request to the next handler.

    On failure: returns a JSON error response immediately — no token or
    PII is included in any log or response body.

    Error mapping (Design §5.1):
        - Missing/malformed header → 401 AUTH_TOKEN_MISSING
        - Expired token            → 401 AUTH_TOKEN_EXPIRED
        - Revoked token            → 401 AUTH_TOKEN_REVOKED
        - Firebase SDK failure     → 503 AUTH_SERVICE_UNAVAILABLE
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

        token = auth_header[len(_BEARER_PREFIX) :]

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
    """FastAPI dependency that verifies the Firebase ID Token.

    Injects the decoded token payload into the route handler.
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
