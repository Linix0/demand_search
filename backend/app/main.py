"""FastAPI application factory and production entrypoint."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.api.v1.exports import router as exports_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.pain_points import router as pain_points_router
from app.api.v1.settings import router as settings_router
from app.api.v1.sources import router as sources_router
from app.api.v1.taxonomy import router as taxonomy_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, error_body
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import Database
from app.schemas.common import RootResponse

logger = structlog.get_logger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an isolated app instance for production, tests, and workers."""

    app_settings = settings or get_settings()
    configure_logging(app_settings)
    docs_enabled = not app_settings.is_production

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        database: Database = app.state.db
        database.dispose()

    app = FastAPI(
        title=app_settings.app_name,
        version=__version__,
        description="Evidence-driven industry pain-point research API",
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.db = Database(app_settings.database_url)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=app_settings.trusted_hosts)
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, _request_id(request), exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {
            "fields": [
                {
                    "location": ".".join(str(part) for part in item.get("loc", ())),
                    "message": item.get("msg", "Invalid value"),
                }
                for item in exc.errors()
            ]
        }
        return JSONResponse(
            status_code=422,
            content=error_body(
                "VALIDATION_ERROR", "Request validation failed.", _request_id(request), details
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        if exc.status_code == 409:
            code = "CONFLICT"
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, message, _request_id(request)),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception", path=request.url.path, error_type=type(exc).__name__
        )
        return JSONResponse(
            status_code=500,
            content=error_body(
                "INTERNAL_ERROR",
                "An unexpected error occurred.",
                _request_id(request),
            ),
        )

    @app.get("/", response_model=RootResponse, tags=["meta"])
    def root() -> RootResponse:
        return RootResponse(
            name=app_settings.app_name,
            version=__version__,
            environment=app_settings.app_env,
            api_prefix="/api/v1",
            docs_enabled=docs_enabled,
        )

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(sources_router)
    app.include_router(pain_points_router)
    app.include_router(taxonomy_router)
    app.include_router(exports_router)
    app.include_router(settings_router)
    return app


app = create_app()
