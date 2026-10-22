"""Durable research job state and bounded configuration snapshot."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobStatus(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStage(StrEnum):
    QUERY_PLANNING = "query_planning"
    SEARCHING = "searching"
    FETCHING = "fetching"
    NORMALIZING = "normalizing"
    EXTRACTING = "extracting"
    VALIDATING_EVIDENCE = "validating_evidence"
    DEDUPLICATING = "deduplicating"
    CLUSTERING = "clustering"
    SCORING = "scoring"
    COMPLETED = "completed"


def _enum_type(enum_class: type[StrEnum], name: str, length: int) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda enum_type: [item.value for item in enum_type],
    )


class ResearchJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "research_jobs"
    __table_args__ = (
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="progress_range"),
        CheckConstraint("cost_limit >= 0", name="cost_limit_non_negative"),
        CheckConstraint("estimated_cost >= 0", name="estimated_cost_non_negative"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[JobStatus] = mapped_column(
        _enum_type(JobStatus, "job_status", 32), nullable=False, default=JobStatus.DRAFT, index=True
    )
    stage: Mapped[JobStage] = mapped_column(
        _enum_type(JobStage, "job_stage", 32), nullable=False, default=JobStage.QUERY_PLANNING
    )
    config_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
    planned_query_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_query_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discovered_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extracted_pain_point_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verified_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    cost_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("5")
    )
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
