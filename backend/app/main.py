"""FastAPI application entry point."""

from fastapi import FastAPI

from app.routers.auth import router as auth_router

app = FastAPI(title="ME API", version="0.1.0")

app.include_router(auth_router)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
