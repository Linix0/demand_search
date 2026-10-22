"""Research job state-transition and worker-delivery idempotency tests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.models.research_job import JobStatus, ResearchJob
from app.services.pipeline import run_research_job


def _create_job(client: TestClient, name: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/research-jobs",
        json={
            "name": name,
            "description": "State transition test",
            "config": {
                "seed_keywords": ["manual reporting"],
                "primary_categories": ["enterprise_ops"],
                "tags": ["repetitive_manual_work"],
                "languages": ["en"],
                "source_providers": ["mock"],
                "max_queries": 2,
                "max_results_per_query": 1,
                "max_total_items": 2,
                "max_job_cost": "5.00",
                "min_evidence_score": 35,
                "dedupe_mode": "balanced",
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _set_status(app, job_id: str, status: JobStatus) -> None:  # type: ignore[no-untyped-def]
    with app.state.db.session_factory() as session:
        session.execute(
            update(ResearchJob).where(ResearchJob.id == uuid.UUID(job_id)).values(status=status)
        )
        session.commit()


def test_invalid_and_duplicate_transitions_return_conflict(client: TestClient) -> None:
    job = _create_job(client, "Transition guard")
    job_id = str(job["id"])
    _set_status(client.app, job_id, JobStatus.QUEUED)

    cases = [
        ("start", "Only draft or failed jobs can be started."),
        ("resume", "Only paused jobs can be resumed."),
        ("retry-failed", "Only failed or partially completed jobs can be retried."),
    ]
    for action, message in cases:
        response = client.post(f"/api/v1/research-jobs/{job_id}/{action}")
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "CONFLICT"
        assert response.json()["error"]["message"] == message

    assert client.get(f"/api/v1/research-jobs/{job_id}").json()["status"] == "queued"


def test_concurrent_queued_job_cannot_be_started_twice(
    client: TestClient, test_settings, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    job = _create_job(client, "Concurrent start")
    job_id = str(job["id"])
    _set_status(client.app, job_id, JobStatus.DRAFT)
    second_client = TestClient(client.app)

    first = client.post(f"/api/v1/research-jobs/{job_id}/start")
    second = second_client.post(f"/api/v1/research-jobs/{job_id}/start")

    assert sorted([first.status_code, second.status_code]) == [200, 409]
    assert client.get(f"/api/v1/research-jobs/{job_id}").json()["status"] == "completed"


def test_paused_job_is_not_claimed_or_run(client: TestClient, app, test_settings) -> None:  # type: ignore[no-untyped-def]
    job = _create_job(client, "Paused job")
    job_id = str(job["id"])
    _set_status(app, job_id, JobStatus.PAUSED)

    with app.state.db.session_factory() as session:
        paused = session.get(ResearchJob, uuid.UUID(job_id))
        assert paused is not None
        result = run_research_job(session, paused, test_settings)
        assert result.status == JobStatus.PAUSED
        session.refresh(paused)
        assert paused.status == JobStatus.PAUSED
        assert paused.started_at is None
        assert paused.planned_query_count == 0


def test_duplicate_worker_delivery_returns_without_rerun(app, test_settings) -> None:  # type: ignore[no-untyped-def]
    from app.tasks import jobs as task_jobs

    job = _create_job(TestClient(app), "Duplicate delivery")
    job_id = str(job["id"])
    _set_status(app, job_id, JobStatus.COMPLETED)

    class FakeTask:
        def retry(self, *, exc: Exception):  # type: ignore[no-untyped-def]
            raise AssertionError(f"Completed jobs must not retry: {exc}")

    task_settings = test_settings.model_copy(
        update={
            "database_url": app.state.settings.database_url,
            "task_execution_mode": "celery",
        }
    )
    original_settings = task_jobs.get_settings
    original_database = task_jobs.Database
    task_jobs.get_settings = lambda: task_settings
    task_jobs.Database = lambda _url: app.state.db
    try:
        result = task_jobs.execute_research_job.run(job_id)
    finally:
        task_jobs.get_settings = original_settings
        task_jobs.Database = original_database

    assert result == {"job_id": job_id, "status": "completed"}
    assert client_status(app, job_id) == "completed"


def client_status(app, job_id: str) -> str:  # type: ignore[no-untyped-def]
    with app.state.db.session_factory() as session:
        job = session.get(ResearchJob, uuid.UUID(job_id))
        assert job is not None
        return job.status.value
