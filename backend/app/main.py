"""FastAPI application entry point."""

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.firebase import get_firebase_app
from app.middleware.auth import AuthMiddleware
from app.routers.auth import router as auth_router
from app.routers.feed import router as feed_router
from app.routers.friends import router as friends_router
from app.routers.history import router as history_router
from app.routers.notifications import router as notifications_router
from app.routers.pets import router as pets_router
from app.routers.posts import router as posts_router
from app.routers.profile import router as profile_router
from app.routers.seen import router as seen_router
from app.routers.settings import router as settings_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ME API",
    version="0.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
)

# Initialise Firebase Admin SDK at startup (optional — graceful if absent).
try:
    fb_app = get_firebase_app()
    if fb_app is None:
        logger.info(
            "Firebase not configured — running in standalone mode"
        )
except Exception:  # noqa: BLE001
    logger.warning(
        "Firebase initialisation failed — push notifications disabled",
        exc_info=True,
    )

# Register JWT token endpoint only in standalone mode.
if settings.auth_mode == "jwt":
    from app.routers.auth_jwt import router as auth_jwt_router

    app.include_router(auth_jwt_router)

# Middleware execution order is LIFO: last-added runs first.
# AuthMiddleware is added first so CORSMiddleware (added last)
# handles OPTIONS preflight before auth checks run.
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(pets_router)
app.include_router(friends_router)
app.include_router(posts_router)
app.include_router(feed_router)
app.include_router(seen_router)
app.include_router(history_router)
app.include_router(settings_router)
app.include_router(notifications_router)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


def _build_openapi() -> dict[str, Any]:
    """Custom OpenAPI schema with BearerAuth security scheme.

    Supports both Firebase ID Token and internal JWT.
    """
    if app.openapi_schema:
        return app.openapi_schema  # type: ignore[return-value]

    auth_description = (
        "Enter your Bearer token.\n\n"
        "• **JWT mode** (`AUTH_MODE=jwt`): obtain via "
        "`POST /auth/token` with your `device_id`.\n"
        "• **Firebase mode** (`AUTH_MODE=firebase`): obtain via "
        "`firebase.auth().currentUser.getIdToken()`."
    )

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description="ME API — paste a Bearer Token into **Authorize**.",
        routes=app.routes,
    )

    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": auth_description,
        }
    }

    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict):
                operation.setdefault(
                    "security", [{"BearerAuth": []}]
                )

    app.openapi_schema = schema
    return schema  # type: ignore[return-value]


app.openapi = _build_openapi  # type: ignore[method-assign]
