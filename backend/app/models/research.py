"""Research job child records, stage logs, and audit history."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class QueryStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ResearchJobLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "research_job_logs"

    research_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SearchQuery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "search_queries"

    research_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent_type: Mapped[str] = mapped_column(String(64), nullable=False, default="pain_discovery")
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="zh-CN")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[QueryStatus] = mapped_column(
        Enum(
            QueryStatus,
            name="query_status",
            native_enum=False,
            length=16,
            values_callable=lambda values: [item.value for item in values],
        ),
        nullable=False,
        default=QueryStatus.PENDING,
    )
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    actor: Mapped[str] = mapped_column(String(160), nullable=False, default="local-user")
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    before_state: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    after_state: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
