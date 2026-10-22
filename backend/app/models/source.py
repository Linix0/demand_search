"""Persisted source pool with traceability and deduplication fields."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContentCompleteness(StrEnum):
    FULL_PUBLIC_CONTENT = "full_public_content"
    PARTIAL_CONTENT = "partial_content"
    SNIPPET_ONLY = "snippet_only"
    METADATA_ONLY = "metadata_only"


class UrlStatus(StrEnum):
    UNCHECKED = "unchecked"
    REACHABLE = "reachable"
    REDIRECTED = "redirected"
    LOGIN_REQUIRED = "login_required"
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


class RetrievalMethod(StrEnum):
    OFFICIAL_API = "official_api"
    SEARCH_API = "search_api"
    MANUAL_IMPORT = "manual_import"
    ALLOWED_PUBLIC_FETCH = "allowed_public_fetch"


class SourceTrustTier(StrEnum):
    A_PRIMARY_USER_REPORT = "A_primary_user_report"
    B_PRIMARY_PRODUCT_FEEDBACK = "B_primary_product_feedback"
    C_SECONDARY_REVIEW = "C_secondary_review"
    D_SEARCH_SNIPPET = "D_search_snippet"
    E_GENERATED_OR_UNVERIFIED = "E_generated_or_unverified"


def _string_enum(enum_class: type[StrEnum], name: str, length: int) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda values: [item.value for item in values],
    )


class SourceItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_items"
    __table_args__ = (
        UniqueConstraint("canonical_url", name="uq_source_items_canonical_url"),
        CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 100", name="relevance_score_range"
        ),
    )

    research_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="SET NULL"), index=True
    )
    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(256), index=True)
    source_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(2_048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2_048), nullable=False)
    final_url: Mapped[str | None] = mapped_column(String(2_048))
    source_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_author_hash: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text)
    content_excerpt: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_completeness: Mapped[ContentCompleteness] = mapped_column(
        _string_enum(ContentCompleteness, "content_completeness", 32),
        nullable=False,
        default=ContentCompleteness.METADATA_ONLY,
    )
    url_status: Mapped[UrlStatus] = mapped_column(
        _string_enum(UrlStatus, "url_status", 32), nullable=False, default=UrlStatus.UNCHECKED
    )
    retrieval_method: Mapped[RetrievalMethod] = mapped_column(
        _string_enum(RetrievalMethod, "retrieval_method", 32),
        nullable=False,
        default=RetrievalMethod.SEARCH_API,
    )
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    source_trust_tier: Mapped[SourceTrustTier] = mapped_column(
        _string_enum(SourceTrustTier, "source_trust_tier", 40),
        nullable=False,
        default=SourceTrustTier.D_SEARCH_SNIPPET,
    )
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_items.id", ondelete="SET NULL")
    )
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
