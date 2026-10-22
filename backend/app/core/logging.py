"""Structured logging configuration with secret redaction."""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from app.core.config import Settings

SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def redact_sensitive_fields(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Mask common credential-bearing keys before any renderer sees them."""

    for key in list(event_dict):
        normalized = key.lower().replace("-", "_")
        if any(part in normalized for part in SENSITIVE_KEY_PARTS):
            event_dict[key] = "[REDACTED]"
        else:
            event_dict[key] = _redact_value(event_dict[key])
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Configure stdlib and structlog consistently for API and workers."""

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)

    renderer: structlog.types.Processor
    if settings.is_production:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_sensitive_fields,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
