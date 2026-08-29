from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from apps.api.config import get_settings
from apps.api.db import engine
from apps.api.migrate import run_migrations
from apps.api.routers import account, admin, auth, catalog, health, orders
from apps.api.security import assert_runtime_secrets, check_rate_limit

# Ensure models are registered on metadata
from apps.api import models as _models  # noqa: F401

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


async def _run_schema_migrations() -> None:
    await asyncio.to_thread(run_migrations)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    assert_runtime_secrets()
    await _run_schema_migrations()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    docs = "/docs" if settings.api_docs_enabled else None
    app = FastAPI(
        title="White Shop API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=docs,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_host_list,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    @app.middleware("http")
    async def security_and_limits(request: Request, call_next):
        try:
            limit_headers = check_rate_limit(request)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=dict(exc.headers or {}),
            )
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        for key, value in (limit_headers or {}).items():
            response.headers.setdefault(key, value)
        forwarded_https = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip() == "https"
        if request.url.scheme == "https" or forwarded_https:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        path = request.url.path
        if (
            path.startswith("/api/v1/admin")
            or path.startswith("/api/v1/orders")
            or path.startswith("/api/v1/me")
            or path.startswith("/api/v1/auth")
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(health.router)
    app.include_router(catalog.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(account.router, prefix="/api/v1")
    app.include_router(orders.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    return app


app = create_app()
