"""Pain points, immutable evidence snapshots, scores, and annotations."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.source import SourceItem
from app.models.taxonomy import TaxonomyCategory


class QuoteMatchStatus(StrEnum):
    EXACT_MATCH = "exact_match"
    NORMALIZED_MATCH = "normalized_match"
    SNIPPET_ONLY = "snippet_only"
    NOT_FOUND = "not_found"


class PainPointStatus(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"
    HYPOTHESIS = "hypothesis"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    ARCHIVED = "archived"


class EvidenceType(StrEnum):
    FIRST_PERSON_PAIN = "first_person_pain"
    FEATURE_REQUEST = "feature_request"
    WORKAROUND = "workaround"
    EXPLICIT_PAYMENT = "explicit_payment"
    COMPETITOR_COMPLAINT = "competitor_complaint"
    TIME_COST = "time_cost"
    FAILURE_COST = "failure_cost"
    QUESTION_OR_HELP = "question_or_help"
    SECONDARY_ANALYSIS = "secondary_analysis"
    OTHER = "other"


class EvidenceRole(StrEnum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CONTEXT = "context"
    PAYMENT_SIGNAL = "payment_signal"


class ManualVerificationStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ScoreType(StrEnum):
    EVIDENCE = "evidence"
    COMMERCIAL = "commercial"
    COVERAGE = "coverage"


def _enum_type(enum_class: type[StrEnum], name: str, length: int) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda values: [item.value for item in values],
    )


class PainPoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pain_points"
    __table_args__ = (
        CheckConstraint(
            "evidence_confidence_score >= 0 AND evidence_confidence_score <= 100",
            name="evidence_score_range",
        ),
        CheckConstraint(
            "commercial_opportunity_score >= 0 AND commercial_opportunity_score <= 100",
            name="commercial_score_range",
        ),
        CheckConstraint(
            "coverage_score >= 0 AND coverage_score <= 100", name="coverage_score_range"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_from_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="SET NULL"), index=True
    )
    primary_category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("taxonomy_categories.id", ondelete="RESTRICT"), index=True
    )
    canonical_statement: Mapped[str] = mapped_column(Text, nullable=False)
    user_segment: Mapped[str] = mapped_column(String(160), nullable=False, default="unknown")
    context: Mapped[str] = mapped_column(Text, nullable=False, default="")
    problem_detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    current_workaround: Mapped[str] = mapped_column(Text, nullable=False, default="")
    current_solution_gap: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pain_type_tags: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list
    )
    status: Mapped[PainPointStatus] = mapped_column(
        _enum_type(PainPointStatus, "pain_point_status", 24),
        nullable=False,
        default=PainPointStatus.CANDIDATE,
        index=True,
    )
    evidence_confidence_score: Mapped[float] = mapped_column(nullable=False, default=0)
    commercial_opportunity_score: Mapped[float] = mapped_column(nullable=False, default=0)
    coverage_score: Mapped[float] = mapped_column(nullable=False, default=0)
    score_version: Mapped[str] = mapped_column(String(32), nullable=False, default="scores-v1")
    distinct_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distinct_thread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payment_signal_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    root_cause_hypotheses: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list
    )
    competitor_summary: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list
    )
    validation_next_step: Mapped[str] = mapped_column(Text, nullable=False, default="")
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pain_points.id", ondelete="SET NULL"), index=True
    )
    last_evidence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[TaxonomyCategory | None] = relationship(lazy="joined")
    evidences: Mapped[list[PainPointEvidence]] = relationship(
        back_populates="pain_point", cascade="all, delete-orphan", order_by="PainPointEvidence.id"
    )
    scores: Mapped[list[PainPointScore]] = relationship(
        back_populates="pain_point",
        cascade="all, delete-orphan",
        order_by="PainPointScore.scored_at",
    )


class PainPointEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pain_point_evidences"
    __table_args__ = (
        UniqueConstraint(
            "pain_point_id",
            "source_item_id",
            "evidence_quote_normalized",
            name="uq_evidence_identity",
        ),
    )

    pain_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pain_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    evidence_quote: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_quote_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    quote_match_status: Mapped[QuoteMatchStatus] = mapped_column(
        _enum_type(QuoteMatchStatus, "quote_match_status", 24), nullable=False
    )
    evidence_type: Mapped[EvidenceType] = mapped_column(
        _enum_type(EvidenceType, "evidence_type", 32), nullable=False
    )
    evidence_role: Mapped[EvidenceRole] = mapped_column(
        _enum_type(EvidenceRole, "evidence_role", 24),
        nullable=False,
        default=EvidenceRole.SUPPORTING,
    )
    evidence_strength_score: Mapped[float] = mapped_column(nullable=False, default=0)
    source_url_snapshot: Mapped[str] = mapped_column(String(2_048), nullable=False)
    target_url: Mapped[str] = mapped_column(String(2_048), nullable=False)
    related_target_urls: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list
    )
    source_published_at_snapshot: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at_snapshot: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    author_independence_key: Mapped[str | None] = mapped_column(String(64))
    manual_verification_status: Mapped[ManualVerificationStatus] = mapped_column(
        _enum_type(ManualVerificationStatus, "manual_verification_status", 24),
        nullable=False,
        default=ManualVerificationStatus.UNREVIEWED,
    )
    manual_note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    pain_point: Mapped[PainPoint] = relationship(back_populates="evidences")
    source_item: Mapped[SourceItem] = relationship(lazy="joined")

    @property
    def source_name(self) -> str:
        return self.source_item.source_name

    @property
    def source_title(self) -> str:
        return self.source_item.source_title

    @property
    def content_completeness(self) -> str:
        return self.source_item.content_completeness.value

    @property
    def retrieval_method(self) -> str:
        return self.source_item.retrieval_method.value

    @property
    def source_trust_tier(self) -> str:
        return self.source_item.source_trust_tier.value


class PainPointScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pain_point_scores"
    __table_args__ = (
        CheckConstraint("total_score >= 0 AND total_score <= 100", name="total_score_range"),
    )

    pain_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pain_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score_type: Mapped[ScoreType] = mapped_column(
        _enum_type(ScoreType, "score_type", 16), nullable=False, index=True
    )
    scoring_version: Mapped[str] = mapped_column(String(32), nullable=False)
    total_score: Mapped[float] = mapped_column(nullable=False)
    dimension_scores: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list
    )
    evidence_ids_used: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list
    )
    calculation_details: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    model_name: Mapped[str | None] = mapped_column(String(160))
    model_suggestion: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql")
    )
    rule_adjustments: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=list
    )
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    pain_point: Mapped[PainPoint] = relationship(back_populates="scores")


class Annotation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "annotations"

    pain_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pain_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    annotation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(160), nullable=False, default="local-user")
