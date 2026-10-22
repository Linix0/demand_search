"""Shared API response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str


class RootResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    environment: str
    api_prefix: str
    docs_enabled: bool
