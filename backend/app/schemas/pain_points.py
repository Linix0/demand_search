"""Pain-point list/detail, evidence, score explanation, and review contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_item_id: uuid.UUID
    evidence_quote: str
    evidence_quote_normalized: str
    quote_match_status: str
    evidence_type: str
    evidence_role: str
    evidence_strength_score: float
    source_url_snapshot: str
    target_url: str
    related_target_urls: list[str]
    source_published_at_snapshot: datetime | None
    collected_at_snapshot: datetime
    author_independence_key: str | None
    manual_verification_status: str
    manual_note: str
    source_name: str = ""
    source_title: str = ""
    content_completeness: str = ""
    retrieval_method: str = ""
    source_trust_tier: str = ""


class ScoreDimensionRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    weight: float
    raw_score: float
    rationale: str


class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    score_type: str
    scoring_version: str
    total_score: float
    dimension_scores: list[dict[str, Any]]
    calculation_details: dict[str, Any]
    rule_adjustments: list[str]
    scored_at: datetime


class PainPointListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    canonical_statement: str
    user_segment: str
    context: str
    status: str
    category: CategoryRead | None
    evidence_confidence_score: float
    commercial_opportunity_score: float
    coverage_score: float
    score_version: str
    distinct_source_count: int
    payment_signal_summary: str
    created_from_job_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class PainPointDetail(PainPointListItem):
    problem_detail: str
    current_workaround: str
    current_solution_gap: str
    pain_type_tags: list[str]
    distinct_thread_count: int
    root_cause_hypotheses: list[dict[str, Any]]
    competitor_summary: list[dict[str, Any]]
    validation_next_step: str
    merged_into_id: uuid.UUID | None
    last_evidence_at: datetime | None
    last_reviewed_at: datetime | None
    evidences: list[EvidenceRead]
    scores: list[ScoreRead]


class PainPointListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PainPointListItem]
    page: int
    page_size: int
    total: int
    coverage_warning: str | None = None


class PainPointPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_statement: str | None = Field(default=None, min_length=10, max_length=2_000)
    user_segment: str | None = Field(default=None, max_length=160)
    context: str | None = Field(default=None, max_length=2_000)
    problem_detail: str | None = Field(default=None, max_length=5_000)
    current_workaround: str | None = Field(default=None, max_length=3_000)
    current_solution_gap: str | None = Field(default=None, max_length=3_000)
    primary_category_code: str | None = Field(default=None, max_length=64)
    pain_type_tags: list[str] | None = Field(default=None, max_length=20)
    validation_next_step: str | None = Field(default=None, max_length=2_000)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="", max_length=2_000)


class RejectRequest(ReviewRequest):
    reason: str = Field(min_length=3, max_length=2_000)


class MergeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_pain_point_id: uuid.UUID
    reason: str = Field(default="", max_length=2_000)


class AnnotationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    annotation_type: Literal["root_cause", "interview", "next_step", "general"] = "general"
    content: str = Field(min_length=2, max_length=5_000)


class AnnotationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    annotation_type: str
    content: str
    actor: str
    created_at: datetime


class ReviewActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pain_point: PainPointDetail
    message: str
