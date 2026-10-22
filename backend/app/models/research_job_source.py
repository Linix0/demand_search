"""Many-to-many membership between research jobs and the shared source pool."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResearchJobSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Link a job to a reusable source without treating the source as job-owned."""

    __tablename__ = "research_job_sources"
    __table_args__ = (
        UniqueConstraint(
            "research_job_id",
            "source_item_id",
            name="uq_research_job_sources_job_source",
        ),
    )

    research_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
