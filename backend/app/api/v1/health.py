"""Health endpoints with independent database and Redis checks."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis import Redis
from redis.exceptions import RedisError

from app import __version__
from app.api.deps import get_app_settings, get_database
from app.core.config import Settings
from app.db.session import Database
from app.schemas.health import ComponentHealth, HealthResponse

router = APIRouter(tags=["health"])


def _database_health(database: Database) -> ComponentHealth:
    started = time.perf_counter()
    try:
        database.ping()
    except Exception:
        return ComponentHealth(status="error", detail="Database ping failed.")
    return ComponentHealth(status="ok", latency_ms=round((time.perf_counter() - started) * 1000, 2))


def _redis_health(settings: Settings) -> ComponentHealth:
    if not settings.redis_enabled:
        return ComponentHealth(status="disabled", detail="Redis is not configured.")

    started = time.perf_counter()
    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=1,
        socket_timeout=1,
        decode_responses=True,
    )
    try:
        client.ping()
    except RedisError:
        return ComponentHealth(status="unavailable", detail="Redis ping failed.")
    finally:
        client.close()
    return ComponentHealth(status="ok", latency_ms=round((time.perf_counter() - started) * 1000, 2))


def _build_health(settings: Settings, database: Database) -> HealthResponse:
    checks = {"database": _database_health(database), "redis": _redis_health(settings)}
    overall: Literal["ok", "degraded", "error"]
    if checks["database"].status != "ok":
        overall = "error"
    elif checks["redis"].status in {"unavailable", "error"}:
        overall = "degraded"
    else:
        overall = "ok"
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        version=__version__,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        checks=checks,
    )


@router.get("/health", response_model=HealthResponse)
def health(
    settings: Annotated[Settings, Depends(get_app_settings)],
    database: Annotated[Database, Depends(get_database)],
) -> HealthResponse | JSONResponse:
    result = _build_health(settings, database)
    if result.status == "error":
        return JSONResponse(status_code=503, content=result.model_dump(mode="json"))
    return result


@router.get("/api/v1/health", response_model=HealthResponse, include_in_schema=False)
def versioned_health(
    settings: Annotated[Settings, Depends(get_app_settings)],
    database: Annotated[Database, Depends(get_database)],
) -> HealthResponse | JSONResponse:
    return health(settings, database)
