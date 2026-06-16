"""FastAPI application factory for the Dokat API Gateway."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.dependency import AuthContext, authenticate_request, get_settings
from app.auth.firebase import init_firebase_app
from app.config import Settings
from app.errors.codes import ErrorCode
from app.errors.handlers import error_response, register_exception_handlers
from app.middleware.trace import TraceMiddleware
from app.routing.matcher import match_route
from app.routing.registry import build_route_table


def _upstream_urls_from_settings(settings: Settings) -> dict[str, str]:
    """Build the route_id → upstream URL mapping from Settings."""
    return {
        "users": str(settings.upstream_user_service_url),
        "pets": str(settings.upstream_pet_service_url),
        "posts": str(settings.upstream_post_service_url),
        "feed": str(settings.upstream_post_service_url),
        "social": str(settings.upstream_social_service_url),
        "capture": str(settings.upstream_capture_service_url),
        "send": str(settings.upstream_send_service_url),
        "view": str(settings.upstream_view_service_url),
        "responses": str(settings.upstream_response_service_url),
        "history": str(settings.upstream_history_service_url),
        "onboarding": str(settings.upstream_onboarding_service_url),
        "notifications": str(settings.upstream_notification_service_url),
        "settings": str(settings.upstream_setting_service_url),
        "ai": str(settings.upstream_ai_api_url),
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise and teardown shared resources.

    Startup:
    - Firebase Admin SDK (gracefully skipped if credentials file is absent).
    - Route table stored in app.state for use by the catch-all handler.

    Placeholders for Redis (T-08).
    """
    settings = get_settings()

    init_firebase_app(settings.firebase_credentials_path)

    upstream_urls = _upstream_urls_from_settings(settings)
    app.state.route_table = build_route_table(
        upstream_urls=upstream_urls,
        capture_rate_limit_per_min=settings.rate_limit_capture_per_min,
    )

    # TODO T-08: initialise Redis connection pool
    yield
    # TODO T-08: close Redis connection pool


def _add_routes(app: FastAPI) -> None:
    """Register all gateway routes on *app*."""

    @app.get("/health", include_in_schema=False)
    async def health(request: Request) -> JSONResponse:
        """Public health stub — no auth required (FR-02.7, FR-06.1).

        Full health aggregation (checking upstream services) is implemented
        in T-10.  This stub returns 200 so that auth integration tests can
        verify the public route bypasses auth.
        """
        return JSONResponse(
            status_code=200,
            content={"status": "ok"},
        )

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        include_in_schema=False,
    )
    async def catch_all(
        request: Request,
        path: str,
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> JSONResponse:
        """Route matching + auth guard for all non-public paths.

        Flow (per design.md §Request lifecycle):
        1. Resolve route via longest-prefix match.
        2. If no match → 404 ROUTE_NOT_FOUND (no auth check needed).
        3. Verify Firebase Bearer token → issue Internal JWT.
        4. Attach AuthContext to request.state (consumed by T-06 forwarder).
        5. Proxy stub: returns 501 until T-06 wires the forwarder.
        """
        trace_id = getattr(request.state, "trace_id", "")
        route_table = getattr(app.state, "route_table", [])

        # Step 1–2: route matching
        route = match_route(f"/{path}", route_table)
        if route is None:
            return JSONResponse(
                status_code=404,
                content=error_response(
                    ErrorCode.ROUTE_NOT_FOUND,
                    f"No route found for '{request.method} /{path}'.",
                    trace_id,
                ),
            )

        # Step 3: auth — raises GatewayError(UNAUTHORIZED) on failure
        auth_header = request.headers.get("authorization", "")
        auth_ctx: AuthContext = authenticate_request(auth_header, settings)

        # Step 4: attach to request state (T-06 will read this)
        request.state.auth = auth_ctx
        request.state.route = route

        # Step 5: proxy stub (T-06 will replace this)
        return JSONResponse(
            status_code=501,
            content=error_response(
                ErrorCode.INTERNAL_ERROR,
                "Proxy forwarding not yet implemented.",
                trace_id,
            ),
        )


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
    _add_routes(app)
    return app


app = create_app()
