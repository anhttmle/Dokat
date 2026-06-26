"""FastAPI application entry point."""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.middleware.auth import FirebaseAuthMiddleware
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

app = FastAPI(
    title="ME API",
    version="0.1.0",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(FirebaseAuthMiddleware)
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
    """Custom OpenAPI schema with Firebase BearerAuth security scheme.

    Adds an ``Authorize`` button to Swagger UI so developers can paste
    a Firebase ID Token and call protected endpoints directly.
    Token persists across page reloads via ``persistAuthorization``.
    """
    if app.openapi_schema:
        return app.openapi_schema  # type: ignore[return-value]

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=(
            "ME API — paste a Firebase ID Token into **Authorize** "
            "to call protected endpoints.\n\n"
            "Get a token: Firebase console → Authentication → "
            "Users → pick a user → copy UID, then use the REST API "
            "or Firebase Emulator to mint a token."
        ),
        routes=app.routes,
    )

    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "Firebase ID Token",
            "description": (
                "Enter your Firebase ID Token. "
                "Obtain via `firebase.auth().currentUser.getIdToken()`."
            ),
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
