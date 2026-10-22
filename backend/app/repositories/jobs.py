"""Research job and log persistence queries."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.research import ResearchJobLog, SearchQuery
from app.models.research_job import JobStatus, ResearchJob


def get_job(session: Session, job_id: uuid.UUID) -> ResearchJob | None:
    return session.get(ResearchJob, job_id)


def list_jobs(
    session: Session,
    *,
    page: int,
    page_size: int,
    status: JobStatus | None = None,
) -> tuple[list[ResearchJob], int]:
    conditions = []
    if status is not None:
        conditions.append(ResearchJob.status == status)

    count_statement = select(func.count()).select_from(ResearchJob).where(*conditions)
    total = session.scalar(count_statement) or 0
    statement = (
        select(ResearchJob)
        .where(*conditions)
        .order_by(ResearchJob.created_at.desc(), ResearchJob.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(session.scalars(statement)), total


def list_job_queries(session: Session, job_id: uuid.UUID) -> list[SearchQuery]:
    statement = (
        select(SearchQuery)
        .where(SearchQuery.research_job_id == job_id)
        .order_by(SearchQuery.priority, SearchQuery.created_at)
    )
    return list(session.scalars(statement))


def list_job_logs(
    session: Session, job_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[ResearchJobLog], int]:
    total = (
        session.scalar(
            select(func.count())
            .select_from(ResearchJobLog)
            .where(ResearchJobLog.research_job_id == job_id)
        )
        or 0
    )
    statement = (
        select(ResearchJobLog)
        .where(ResearchJobLog.research_job_id == job_id)
        .order_by(ResearchJobLog.created_at.asc(), ResearchJobLog.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(session.scalars(statement)), total
