"""Stable application error codes and response envelopes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AppError(Exception):
    """A domain error that is safe to expose to API clients."""

    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class UrlSafetyError(AppError):
    """Raised when a URL violates the outbound-fetch safety policy."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=400)


def error_body(
    code: str, message: str, request_id: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the documented API error envelope."""

    return {
        "error": {"code": code, "message": message, "details": details or {}},
        "request_id": request_id,
    }
