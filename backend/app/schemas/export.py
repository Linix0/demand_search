"""Export request contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["csv", "json", "markdown"]
    job_id: str | None = None
    status: str | None = None
    max_items: int = Field(default=1_000, ge=1, le=5_000)
