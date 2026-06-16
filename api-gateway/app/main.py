"""FastAPI application factory for the Dokat API Gateway."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.errors.handlers import register_exception_handlers
from app.middleware.trace import TraceMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise and teardown shared resources.

    Placeholders for Redis connection pool and Firebase Admin SDK will be
    added in subsequent tasks (T-05, T-08).
    """
    # TODO T-05: initialise Firebase Admin SDK
    # TODO T-08: initialise Redis connection pool
    yield
    # TODO T-05: close Firebase Admin app
    # TODO T-08: close Redis connection pool


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Dokat API Gateway",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.add_middleware(TraceMiddleware)
    return app


app = create_app()
