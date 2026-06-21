"""FastAPI application entry point."""

from fastapi import FastAPI

from app.middleware.auth import FirebaseAuthMiddleware
from app.routers.auth import router as auth_router
from app.routers.pets import router as pets_router
from app.routers.profile import router as profile_router

app = FastAPI(title="ME API", version="0.1.0")

app.add_middleware(FirebaseAuthMiddleware)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(pets_router)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
