"""End-to-end offline evidence, review, and export behavior."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.services.pipeline as pipeline
from app.models.pain_point import (
    EvidenceRole,
    PainPoint,
    PainPointEvidence,
)
from app.models.research_job import JobStatus, ResearchJob
from app.models.source import SourceItem
from app.providers.llm.base import ExtractionRequest, ExtractionResponse
from app.providers.search.base import ProviderCapabilities, SearchRequest, SearchResult
from app.services.pipeline import run_research_job


class _PaymentGuidanceSearchProvider:
    code = "mock"
    display_name = "Mock Search"
    capabilities = ProviderCapabilities(keyword_search=True)

    def search(self, request: SearchRequest) -> list[SearchResult]:
        return [
            SearchResult(
                provider_code=self.code,
                external_id="payment-rule-label-only",
                title="Weekly spreadsheet reconciliation",
                url="https://example.com/mock/payment-rule-label-only",
                snippet="Every week I copy the same fields into a spreadsheet and miss records.",
                published_at=datetime(2026, 10, 2, 8, 0, tzinfo=UTC),
                metadata={
                    "content_completeness": "full_public_content",
                    "trust_tier": "A_primary_user_report",
                    "author": "payment-rule-alpha",
                },
            ),
            SearchResult(
                provider_code=self.code,
                external_id="payment-rule-verified-quote",
                title="A paid tool still misses our workflow",
                url="https://example.com/mock/payment-rule-verified-quote",
                snippet=(
                    "Our team already paid for a tool, but it still lacks the workflow we need."
                ),
                published_at=datetime(2026, 10, 2, 8, 0, tzinfo=UTC),
                metadata={
                    "content_completeness": "full_public_content",
                    "trust_tier": "A_primary_user_report",
                    "author": "payment-rule-beta",
                },
            ),
        ]


class _SnippetSourceSearchProvider(_PaymentGuidanceSearchProvider):
    def search(self, request: SearchRequest) -> list[SearchResult]:
        results = super().search(request)
        return [
            SearchResult(
                provider_code=item.provider_code,
                external_id=item.external_id,
                title=item.title,
                url=item.url,
                snippet=item.snippet,
                published_at=item.published_at,
                author=item.author,
                metadata={**item.metadata, "content_completeness": "snippet_only"},
            )
            for item in results[:1]
        ]


class _PaymentGuidanceLLM:
    code = "mock"

    def extract_candidates(self, request: ExtractionRequest) -> ExtractionResponse:
        if "already paid for a tool" in request.source_text:
            statement = "A purchased tool still leaves the team without the workflow it needs."
            quote = "Our team already paid for a tool, but it still lacks the workflow we need."
            payment_label = "none"
        else:
            statement = "The team copies records into a spreadsheet every week and misses some."
            quote = "Every week I copy the same fields into a spreadsheet and miss records."
            payment_label = "explicit"
        return ExtractionResponse(
            source_item_id=request.source_item_id,
            candidates=[
                {
                    "source_item_id": request.source_item_id,
                    "pain_statement": statement,
                    "user_segment": "small_business",
                    "context": "Manual workflow",
                    "problem_detail": "The team lacks a reliable workflow for its records.",
                    "current_workaround": "spreadsheet",
                    "payment_signal": payment_label,
                    "evidence_quote": quote,
                    "candidate_type": "first_person_pain",
                    "tags": ["repetitive_manual_work"],
                    "uncertainties": [],
                }
            ],
        )


def _run_demo(client: TestClient) -> dict[str, object]:
    response = client.post("/api/v1/research-jobs/demo")
    assert response.status_code == 200, response.text
    return response.json()


def test_demo_produces_traceable_candidates_and_exports(client: TestClient) -> None:
    body = _run_demo(client)
    job = body["job"]

    assert job["status"] == "completed"
    assert job["discovered_source_count"] == 30
    assert job["extracted_pain_point_count"] >= 30
    assert job["progress_percent"] == 100

    listing = client.get(
        "/api/v1/pain-points", params={"page_size": 5, "sort_by": "evidence_score"}
    )
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] >= 30
    assert len(payload["items"]) == 5
    assert (
        payload["items"][0]["evidence_confidence_score"]
        != payload["items"][0]["commercial_opportunity_score"]
    )

    detail_response = client.get(f"/api/v1/pain-points/{payload['items'][0]['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["evidences"]
    assert detail["scores"]
    assert {score["score_type"] for score in detail["scores"]} == {
        "evidence",
        "commercial",
        "coverage",
    }
    evidence = detail["evidences"][0]
    assert evidence["source_url_snapshot"].startswith("https://")
    assert evidence["source_name"] == "Mock Search"
    assert evidence["collected_at_snapshot"]

    all_items = client.get("/api/v1/pain-points", params={"page_size": 100}).json()["items"]
    assert len(all_items) >= 30
    evidence_records = 0
    for item in all_items:
        item_detail = client.get(f"/api/v1/pain-points/{item['id']}").json()
        assert item_detail["evidences"], "every fact-level candidate must retain evidence"
        evidence_records += len(item_detail["evidences"])
    assert evidence_records >= len(all_items)

    csv_response = client.post("/api/v1/exports/pain-points", json={"format": "csv"})
    assert csv_response.status_code == 200
    assert int(csv_response.headers["X-Export-Rows"]) >= 30
    rows = list(csv.DictReader(io.StringIO(csv_response.text)))
    assert rows[0]["primary_source_url"].startswith("https://")
    assert rows[0]["evidence_quotes"]
    assert rows[0]["score_version"] == "scores-v1"

    json_response = client.post("/api/v1/exports/pain-points", json={"format": "json"})
    assert json_response.status_code == 200
    exported = json.loads(json_response.text)
    assert exported["schema_version"] == "1.0"
    assert exported["items"][0]["all_source_urls"].startswith("https://")

    markdown_response = client.post("/api/v1/exports/pain-points", json={"format": "markdown"})
    assert markdown_response.status_code == 200
    assert "## 1." in markdown_response.text
    assert "https://example.com/mock/" in markdown_response.text
    assert "not market facts" in markdown_response.text


def test_demo_reuses_shared_sources_without_losing_job_outputs(client: TestClient) -> None:
    first = _run_demo(client)["job"]
    second = _run_demo(client)["job"]

    for job in (first, second):
        assert job["status"] == "completed"
        assert job["discovered_source_count"] == 30
        assert job["extracted_pain_point_count"] >= 30

    for job in (first, second):
        sources = client.get(
            "/api/v1/source-items", params={"job_id": job["id"], "page_size": 100}
        ).json()
        pain_points = client.get(
            "/api/v1/pain-points", params={"job_id": job["id"], "page_size": 100}
        ).json()
        assert sources["total"] == 30
        assert pain_points["total"] >= 30
        assert all(item["created_from_job_id"] == job["id"] for item in pain_points["items"])


def test_verification_requires_verified_quote(client: TestClient) -> None:
    _run_demo(client)
    listing = client.get("/api/v1/pain-points", params={"page_size": 100}).json()
    hypothesis = next(item for item in listing["items"] if item["status"] == "hypothesis")
    verifiable = next(item for item in listing["items"] if item["status"] == "needs_review")

    rejected = client.post(
        f"/api/v1/pain-points/{hypothesis['id']}/verify", json={"reason": "Check quote"}
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "EVIDENCE_QUOTE_NOT_VERIFIED"

    verified = client.post(
        f"/api/v1/pain-points/{verifiable['id']}/verify",
        json={"reason": "Opened the source and confirmed the quote."},
    )
    assert verified.status_code == 200
    assert verified.json()["pain_point"]["status"] == "verified"


def test_merge_preserves_and_reassembles_evidence(client: TestClient) -> None:
    _run_demo(client)
    items = client.get("/api/v1/pain-points", params={"page_size": 100}).json()["items"]
    source, target = items[0], items[1]

    response = client.post(
        f"/api/v1/pain-points/{source['id']}/merge",
        json={"target_pain_point_id": target["id"], "reason": "Same workflow problem"},
    )
    assert response.status_code == 200, response.text
    merged_target = response.json()["pain_point"]
    assert len(merged_target["evidences"]) >= 2
    assert merged_target["distinct_source_count"] >= 2

    source_detail = client.get(f"/api/v1/pain-points/{source['id']}").json()
    assert source_detail["status"] == "duplicate"
    assert source_detail["merged_into_id"] == target["id"]

    logs = client.get(f"/api/v1/research-jobs/{source['created_from_job_id']}/logs").json()
    assert logs["total"] >= 3


def test_manual_import_blocks_private_targets(client: TestClient) -> None:
    response = client.post(
        "/api/v1/source-items/import-url", json={"url": "http://127.0.0.1/private"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SSRF_BLOCKED"


def test_list_rejects_unknown_filter_values(client: TestClient) -> None:
    response = client.get("/api/v1/pain-points", params={"sort_by": "evidence+commercial"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_taxonomy_is_database_backed(client: TestClient) -> None:
    categories = client.get("/api/v1/taxonomy/categories")
    tags = client.get("/api/v1/taxonomy/tags")

    assert categories.status_code == 200
    assert any(item["code"] == "enterprise_ops" for item in categories.json()["items"])
    assert tags.status_code == 200
    assert any(item["code"] == "repetitive_manual_work" for item in tags.json()["items"])


def test_snippet_only_payment_text_remains_supporting_evidence(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline, "MockSearchProvider", _SnippetSourceSearchProvider)
    created = client.post(
        "/api/v1/research-jobs",
        json={
            "name": "Snippet payment fixture",
            "config": {
                "seed_keywords": ["manual reporting"],
                "primary_categories": ["enterprise_ops"],
                "languages": ["en"],
                "source_providers": ["mock"],
                "max_queries": 1,
                "max_results_per_query": 1,
                "max_total_items": 1,
            },
        },
    )
    assert created.status_code == 201, created.text
    job_id = uuid.UUID(created.json()["id"])
    with client.app.state.db.session_factory() as session:
        job = session.get(ResearchJob, job_id)
        assert job is not None
        job.status = JobStatus.QUEUED
        session.commit()
        result = run_research_job(
            session,
            job,
            client.app.state.settings,
            search_provider=_SnippetSourceSearchProvider(),
            llm_provider=_PaymentGuidanceLLM(),
        )
        assert result.status == JobStatus.COMPLETED

    with client.app.state.db.session_factory() as session:
        evidence = session.scalar(
            select(PainPointEvidence)
            .join(SourceItem)
            .where(SourceItem.external_id == "payment-rule-label-only")
        )
        assert evidence is not None
        assert evidence.quote_match_status.value == "snippet_only"
        assert evidence.evidence_role == EvidenceRole.SUPPORTING
        assert evidence.pain_point.payment_signal_summary == ""


def test_payment_role_and_scoring_follow_verified_quote_not_model_label(
    client: TestClient,
) -> None:
    created = client.post(
        "/api/v1/research-jobs",
        json={
            "name": "Payment rule integration fixture",
            "config": {
                "seed_keywords": ["manual reporting"],
                "primary_categories": ["enterprise_ops"],
                "languages": ["en"],
                "source_providers": ["mock"],
                "max_queries": 1,
                "max_results_per_query": 2,
                "max_total_items": 2,
            },
        },
    )
    assert created.status_code == 201, created.text
    job_id = uuid.UUID(created.json()["id"])

    with client.app.state.db.session_factory() as session:
        job = session.get(ResearchJob, job_id)
        assert job is not None
        job.status = JobStatus.QUEUED
        session.commit()
        completed = run_research_job(
            session,
            job,
            client.app.state.settings,
            search_provider=_PaymentGuidanceSearchProvider(),
            llm_provider=_PaymentGuidanceLLM(),
        )
        assert completed.status == JobStatus.COMPLETED

    with client.app.state.db.session_factory() as session:
        rows = list(
            session.scalars(
                select(PainPointEvidence).where(
                    PainPointEvidence.source_item_id.in_(
                        select(SourceItem.id).where(
                            SourceItem.external_id.in_(
                                {"payment-rule-label-only", "payment-rule-verified-quote"}
                            )
                        )
                    )
                )
            )
        )
        evidence_by_external_id = {row.source_item.external_id: row for row in rows}
        label_only = evidence_by_external_id["payment-rule-label-only"]
        paid = evidence_by_external_id["payment-rule-verified-quote"]
        label_only_point = session.get(PainPoint, label_only.pain_point_id)
        paid_point = session.get(PainPoint, paid.pain_point_id)
        assert label_only_point is not None
        assert paid_point is not None

        assert label_only.quote_match_status.value == "exact_match"
        assert paid.quote_match_status.value == "exact_match"
        assert label_only.evidence_role == EvidenceRole.SUPPORTING
        assert paid.evidence_role == EvidenceRole.PAYMENT_SIGNAL
        assert label_only_point.payment_signal_summary == ""
        assert paid_point.payment_signal_summary
        assert (
            paid_point.commercial_opportunity_score > label_only_point.commercial_opportunity_score
        )
