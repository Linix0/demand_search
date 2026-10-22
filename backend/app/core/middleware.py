"""Request correlation, security headers, and bounded request logging."""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a server-generated request ID and baseline security headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()

        with structlog.contextvars.bound_contextvars(request_id=request_id):
            try:
                response = await call_next(request)
            except Exception:
                logger.exception(
                    "request_failed",
                    method=request.method,
                    path=request.url.path,
                )
                raise

            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
