"""Source pool persistence and deduplication queries."""

from __future__ import annotations

import uuid

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.models.research_job_source import ResearchJobSource
from app.models.source import ContentCompleteness, SourceItem


def find_source_by_canonical_url(session: Session, canonical_url: str) -> SourceItem | None:
    statement = select(SourceItem).where(SourceItem.canonical_url == canonical_url)
    return session.scalar(statement)


def find_source_by_external_id(
    session: Session, provider_code: str, external_id: str
) -> SourceItem | None:
    statement = select(SourceItem).where(
        SourceItem.provider_code == provider_code,
        SourceItem.external_id == external_id,
    )
    return session.scalar(statement)


def get_source(session: Session, source_id: uuid.UUID) -> SourceItem | None:
    return session.get(SourceItem, source_id)


def list_sources(
    session: Session,
    *,
    page: int,
    page_size: int,
    job_id: uuid.UUID | None = None,
    provider_code: str | None = None,
    source_domain: str | None = None,
    completeness: ContentCompleteness | None = None,
    query: str | None = None,
) -> tuple[list[SourceItem], int]:
    conditions: list[ColumnElement[bool]] = []
    if job_id is not None:
        conditions.append(
            SourceItem.id.in_(
                select(ResearchJobSource.source_item_id).where(
                    ResearchJobSource.research_job_id == job_id
                )
            )
        )
    if provider_code:
        conditions.append(SourceItem.provider_code == provider_code)
    if source_domain:
        conditions.append(SourceItem.source_domain == source_domain)
    if completeness is not None:
        conditions.append(SourceItem.content_completeness == completeness)
    if query:
        pattern = f"%{query.strip()}%"
        conditions.append(
            or_(SourceItem.source_title.ilike(pattern), SourceItem.source_url.ilike(pattern))
        )

    total = session.scalar(select(func.count()).select_from(SourceItem).where(*conditions)) or 0
    statement = (
        select(SourceItem)
        .where(*conditions)
        .order_by(SourceItem.collected_at.desc(), SourceItem.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(session.scalars(statement)), total


def has_job_source(session: Session, job_id: uuid.UUID, source_id: uuid.UUID) -> bool:
    statement = select(ResearchJobSource.id).where(
        ResearchJobSource.research_job_id == job_id,
        ResearchJobSource.source_item_id == source_id,
    )
    return session.scalar(statement) is not None


def link_job_source(session: Session, job_id: uuid.UUID, source_id: uuid.UUID) -> bool:
    """Link a source to a job once; return True when the link is new."""

    if has_job_source(session, job_id, source_id):
        return False
    session.add(ResearchJobSource(research_job_id=job_id, source_item_id=source_id))
    session.flush()
    return True
