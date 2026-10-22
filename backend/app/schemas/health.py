"""Health check response contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ComponentHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "unavailable", "disabled", "error"]
    latency_ms: float | None = Field(default=None, ge=0)
    detail: str | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded", "error"]
    service: str
    version: str
    environment: str
    timestamp: datetime
    checks: dict[str, ComponentHealth]
