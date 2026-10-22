"""Source pool and manual import contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    research_job_id: uuid.UUID | None
    provider_code: str
    external_id: str | None
    source_name: str
    source_domain: str
    source_url: str
    canonical_url: str
    final_url: str | None
    source_title: str
    published_at: datetime | None
    collected_at: datetime
    content_excerpt: str | None
    content_completeness: str
    url_status: str
    retrieval_method: str
    relevance_score: int
    source_trust_tier: str
    is_duplicate: bool
    duplicate_of_id: uuid.UUID | None


class SourceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SourceRead]
    page: int
    page_size: int
    total: int


class ManualUrlImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=8, max_length=2_048)
    title: str = Field(default="", max_length=300)


class UrlRecheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: SourceRead
    message: str
