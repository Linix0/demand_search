"""Research job creation, progress, and log contracts."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_keywords: list[str] = Field(min_length=1, max_length=5)
    primary_categories: list[str] = Field(default_factory=lambda: ["other"], max_length=5)
    tags: list[str] = Field(default_factory=list, max_length=20)
    languages: list[str] = Field(default_factory=lambda: ["zh-CN"], max_length=2)
    source_providers: list[str] = Field(default_factory=lambda: ["mock"], max_length=5)
    max_queries: int = Field(default=10, ge=1, le=20)
    max_results_per_query: int = Field(default=3, ge=1, le=30)
    max_total_items: int = Field(default=60, ge=1, le=200)
    max_job_cost: Decimal = Field(default=Decimal("5.00"), ge=0, le=100)
    min_evidence_score: int = Field(default=35, ge=0, le=100)
    dedupe_mode: str = Field(default="balanced", pattern="^(strict|balanced|recall)$")

    @model_validator(mode="after")
    def normalize_keywords(self) -> JobConfigRequest:
        self.seed_keywords = [value.strip() for value in self.seed_keywords if value.strip()]
        if not self.seed_keywords:
            raise ValueError("At least one non-empty seed keyword is required")
        if any(len(value) > 120 for value in self.seed_keywords):
            raise ValueError("Seed keywords must be at most 120 characters")
        return self


class JobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2_000)
    date_from: date | None = None
    date_to: date | None = None
    config: JobConfigRequest

    @model_validator(mode="after")
    def validate_dates(self) -> JobCreateRequest:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    status: str
    stage: str
    config_json: dict[str, Any]
    date_from: date | None
    date_to: date | None
    planned_query_count: int
    processed_query_count: int
    discovered_source_count: int
    processed_source_count: int
    extracted_pain_point_count: int
    verified_evidence_count: int
    estimated_cost: Decimal
    cost_limit: Decimal
    progress_percent: int
    error_summary: str | None
    started_at: datetime | None
    finished_at: datetime | None
    paused_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[JobRead]
    page: int
    page_size: int
    total: int


class JobLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage: str
    level: str
    message: str
    detail: dict[str, Any]
    created_at: datetime


class JobLogListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[JobLogRead]
    page: int
    page_size: int
    total: int


class JobActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job: JobRead
    message: str
