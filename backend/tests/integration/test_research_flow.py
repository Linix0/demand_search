"""End-to-end offline evidence, review, and export behavior."""

from __future__ import annotations

import csv
import io
import json

from fastapi.testclient import TestClient


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
