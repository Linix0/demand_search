"""Research job lifecycle, controls, and durable progress updates."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.models.research import ResearchJobLog
from app.models.research_job import JobStage, JobStatus, ResearchJob
from app.models.taxonomy import TaxonomyCategory
from app.repositories.jobs import get_job, list_job_logs, list_jobs
from app.schemas.research import JobConfigRequest, JobCreateRequest
from app.services.audit import write_audit
from app.services.workspace import ensure_default_workspace


def create_job(session: Session, payload: JobCreateRequest) -> ResearchJob:
    workspace = ensure_default_workspace(session)
    category_codes = set(session.scalars(select(TaxonomyCategory.code)))
    unknown_categories = sorted(set(payload.config.primary_categories) - category_codes)
    if unknown_categories:
        raise AppError(
            "VALIDATION_ERROR",
            "Unknown taxonomy categories.",
            status_code=422,
            details={"categories": unknown_categories},
        )
    unsupported_providers = sorted(set(payload.config.source_providers) - {"mock"})
    if unsupported_providers:
        raise AppError(
            "PROVIDER_DISABLED",
            "Requested source providers are not enabled.",
            status_code=409,
            details={"providers": unsupported_providers},
        )

    job = ResearchJob(
        workspace_id=workspace.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        status=JobStatus.DRAFT,
        stage=JobStage.QUERY_PLANNING,
        config_json=payload.config.model_dump(mode="json"),
        date_from=payload.date_from,
        date_to=payload.date_to,
        cost_limit=payload.config.max_job_cost,
        estimated_cost="0",
        progress_percent=0,
    )
    session.add(job)
    session.flush()
    write_audit(
        session,
        action="job_created",
        entity_type="research_job",
        entity_id=job.id,
        after_state={"status": job.status.value, "name": job.name},
    )
    session.commit()
    session.refresh(job)
    return job


def get_job_or_error(session: Session, job_id: uuid.UUID) -> ResearchJob:
    job = get_job(session, job_id)
    if job is None:
        raise AppError("RESOURCE_NOT_FOUND", "Research job not found.", status_code=404)
    return job


def get_jobs(
    session: Session, *, page: int, page_size: int, status: JobStatus | None = None
) -> tuple[list[ResearchJob], int]:
    return list_jobs(session, page=page, page_size=page_size, status=status)


def get_logs(
    session: Session, job_id: uuid.UUID, *, page: int, page_size: int
) -> tuple[list[ResearchJobLog], int]:
    get_job_or_error(session, job_id)
    return list_job_logs(session, job_id, page=page, page_size=page_size)


def add_job_log(
    session: Session,
    job: ResearchJob,
    *,
    stage: str,
    message: str,
    level: str = "info",
    detail: dict[str, object] | None = None,
) -> None:
    session.add(
        ResearchJobLog(
            research_job_id=job.id,
            stage=stage,
            level=level,
            message=message,
            detail=detail or {},
            created_at=datetime.now(UTC),
        )
    )


def start_job(session: Session, job_id: uuid.UUID, settings: Settings) -> ResearchJob:
    job = get_job_or_error(session, job_id)
    if job.status not in {JobStatus.DRAFT, JobStatus.QUEUED, JobStatus.FAILED}:
        raise AppError(
            "CONFLICT",
            "Only draft, queued, or failed jobs can be started.",
            status_code=409,
            details={"status": job.status.value},
        )
    before = job.status.value
    job.status = JobStatus.QUEUED
    job.paused_at = None
    write_audit(
        session,
        action="job_started",
        entity_type="research_job",
        entity_id=job.id,
        before_state={"status": before},
        after_state={"status": job.status.value},
    )
    session.commit()
    session.refresh(job)

    if settings.task_execution_mode == "celery":
        from app.tasks.jobs import enqueue_research_job

        enqueue_research_job(str(job.id))
        return job

    from app.services.pipeline import run_research_job

    return run_research_job(session, job, settings)


def pause_job(session: Session, job_id: uuid.UUID) -> ResearchJob:
    job = get_job_or_error(session, job_id)
    if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
        raise AppError("CONFLICT", "Only queued or running jobs can be paused.", status_code=409)
    prior = job.status.value
    job.status = JobStatus.PAUSED
    job.paused_at = datetime.now(UTC)
    write_audit(
        session,
        action="job_paused",
        entity_type="research_job",
        entity_id=job.id,
        before_state={"status": prior},
        after_state={"status": job.status.value},
    )
    session.commit()
    session.refresh(job)
    return job


def resume_job(session: Session, job_id: uuid.UUID, settings: Settings) -> ResearchJob:
    job = get_job_or_error(session, job_id)
    if job.status not in {JobStatus.PAUSED, JobStatus.QUEUED}:
        raise AppError("CONFLICT", "Only paused or queued jobs can be resumed.", status_code=409)
    prior = job.status.value
    job.status = JobStatus.QUEUED
    job.paused_at = None
    write_audit(
        session,
        action="job_resumed",
        entity_type="research_job",
        entity_id=job.id,
        before_state={"status": prior},
        after_state={"status": job.status.value},
    )
    session.commit()
    session.refresh(job)
    if settings.task_execution_mode == "celery":
        from app.tasks.jobs import enqueue_research_job

        enqueue_research_job(str(job.id))
        return job
    from app.services.pipeline import run_research_job

    return run_research_job(session, job, settings)


def cancel_job(session: Session, job_id: uuid.UUID) -> ResearchJob:
    job = get_job_or_error(session, job_id)
    if job.status in {JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.COMPLETED_WITH_ERRORS}:
        raise AppError("CONFLICT", "The job can no longer be cancelled.", status_code=409)
    prior = job.status.value
    job.status = JobStatus.CANCELLED
    job.finished_at = datetime.now(UTC)
    write_audit(
        session,
        action="job_cancelled",
        entity_type="research_job",
        entity_id=job.id,
        before_state={"status": prior},
        after_state={"status": job.status.value},
    )
    session.commit()
    session.refresh(job)
    return job


def duplicate_job(session: Session, job_id: uuid.UUID) -> ResearchJob:
    source = get_job_or_error(session, job_id)
    payload = JobCreateRequest(
        name=f"{source.name} (copy)",
        description=source.description,
        date_from=source.date_from,
        date_to=source.date_to,
        config=JobConfigRequest.model_validate(source.config_json),
    )
    return create_job(session, payload)


def retry_failed_job(session: Session, job_id: uuid.UUID, settings: Settings) -> ResearchJob:
    job = get_job_or_error(session, job_id)
    if job.status not in {JobStatus.FAILED, JobStatus.COMPLETED_WITH_ERRORS}:
        raise AppError(
            "CONFLICT",
            "Only failed or partially completed jobs can be retried.",
            status_code=409,
        )
    prior = job.status.value
    job.status = JobStatus.QUEUED
    job.error_summary = None
    write_audit(
        session,
        action="job_retried",
        entity_type="research_job",
        entity_id=job.id,
        before_state={"status": prior},
        after_state={"status": job.status.value},
    )
    session.commit()
    session.refresh(job)
    if settings.task_execution_mode == "celery":
        from app.tasks.jobs import enqueue_research_job

        enqueue_research_job(str(job.id))
        return job
    from app.services.pipeline import run_research_job

    return run_research_job(session, job, settings)
