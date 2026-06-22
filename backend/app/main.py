"""FastAPI application entry point."""

from fastapi import FastAPI

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

app = FastAPI(title="ME API", version="0.1.0")

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
