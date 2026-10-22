"""Thin Celery entrypoints; durable state remains in PostgreSQL."""

from __future__ import annotations

import uuid

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import Database
from app.models.research_job import JobStatus, ResearchJob
from app.services.pipeline import run_research_job
from app.tasks.celery_app import celery_app


@celery_app.task(name="research_jobs.execute", bind=True, max_retries=2)
def execute_research_job(self, job_id: str) -> dict[str, str]:  # type: ignore[no-untyped-def]
    settings = get_settings()
    configure_logging(settings)
    database = Database(settings.database_url)
    session = database.session_factory()
    try:
        job = session.get(ResearchJob, uuid.UUID(job_id))
        if job is None:
            return {"job_id": job_id, "status": "not_found"}
        if job.status in {JobStatus.CANCELLED, JobStatus.COMPLETED}:
            return {"job_id": job_id, "status": job.status.value}
        job = run_research_job(session, job, settings)
        return {"job_id": str(job.id), "status": job.status.value}
    finally:
        session.close()
        database.dispose()


def enqueue_research_job(job_id: str) -> None:
    execute_research_job.delay(job_id)
