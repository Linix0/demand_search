"""Research job CRUD, controls, logs, and the offline demo entrypoint."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db_session
from app.core.config import Settings
from app.models.research_job import JobStatus
from app.schemas.research import (
    JobActionResponse,
    JobConfigRequest,
    JobCreateRequest,
    JobListResponse,
    JobLogListResponse,
    JobLogRead,
    JobRead,
)
from app.services.jobs import (
    cancel_job,
    create_job,
    duplicate_job,
    get_job_or_error,
    get_jobs,
    get_logs,
    pause_job,
    resume_job,
    retry_failed_job,
    start_job,
)

router = APIRouter(prefix="/api/v1/research-jobs", tags=["research-jobs"])
SessionDep = Annotated[Session, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_research_job(payload: JobCreateRequest, session: SessionDep) -> JobRead:
    return JobRead.model_validate(create_job(session, payload))


@router.post("/demo", response_model=JobActionResponse)
def run_demo_job(session: SessionDep, settings: SettingsDep) -> JobActionResponse:
    payload = JobCreateRequest(
        name="Offline evidence demo",
        description=(
            "Deterministic Mock research task used to verify the source-to-evidence loop "
            "without external API keys."
        ),
        config=JobConfigRequest(
            seed_keywords=["manual reporting", "spreadsheet reconciliation"],
            primary_categories=["enterprise_ops"],
            tags=["repetitive_manual_work"],
            languages=["en"],
            source_providers=["mock"],
            max_queries=10,
            max_results_per_query=3,
            max_total_items=60,
            max_job_cost=Decimal("5.00"),
            min_evidence_score=35,
            dedupe_mode="balanced",
        ),
    )
    job = create_job(session, payload)
    job = start_job(session, job.id, settings)
    return JobActionResponse(job=JobRead.model_validate(job), message="Demo job completed.")


@router.get("", response_model=JobListResponse)
def list_research_jobs(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    job_status: Annotated[JobStatus | None, Query(alias="status")] = None,
) -> JobListResponse:
    items, total = get_jobs(session, page=page, page_size=page_size, status=job_status)
    return JobListResponse(
        items=[JobRead.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{job_id}", response_model=JobRead)
def get_research_job(job_id: uuid.UUID, session: SessionDep) -> JobRead:
    return JobRead.model_validate(get_job_or_error(session, job_id))


@router.post("/{job_id}/start", response_model=JobActionResponse)
def start_research_job(
    job_id: uuid.UUID, session: SessionDep, settings: SettingsDep
) -> JobActionResponse:
    job = start_job(session, job_id, settings)
    return JobActionResponse(job=JobRead.model_validate(job), message="Research job started.")


@router.post("/{job_id}/pause", response_model=JobActionResponse)
def pause_research_job(job_id: uuid.UUID, session: SessionDep) -> JobActionResponse:
    job = pause_job(session, job_id)
    return JobActionResponse(job=JobRead.model_validate(job), message="Research job paused.")


@router.post("/{job_id}/resume", response_model=JobActionResponse)
def resume_research_job(
    job_id: uuid.UUID, session: SessionDep, settings: SettingsDep
) -> JobActionResponse:
    job = resume_job(session, job_id, settings)
    return JobActionResponse(job=JobRead.model_validate(job), message="Research job resumed.")


@router.post("/{job_id}/cancel", response_model=JobActionResponse)
def cancel_research_job(job_id: uuid.UUID, session: SessionDep) -> JobActionResponse:
    job = cancel_job(session, job_id)
    return JobActionResponse(job=JobRead.model_validate(job), message="Research job cancelled.")


@router.post("/{job_id}/retry-failed", response_model=JobActionResponse)
def retry_research_job(
    job_id: uuid.UUID, session: SessionDep, settings: SettingsDep
) -> JobActionResponse:
    job = retry_failed_job(session, job_id, settings)
    return JobActionResponse(job=JobRead.model_validate(job), message="Retry completed.")


@router.post("/{job_id}/duplicate", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def duplicate_research_job(job_id: uuid.UUID, session: SessionDep) -> JobRead:
    return JobRead.model_validate(duplicate_job(session, job_id))


@router.get("/{job_id}/logs", response_model=JobLogListResponse)
def list_research_job_logs(
    job_id: uuid.UUID,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JobLogListResponse:
    items, total = get_logs(session, job_id, page=page, page_size=page_size)
    return JobLogListResponse(
        items=[JobLogRead.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
