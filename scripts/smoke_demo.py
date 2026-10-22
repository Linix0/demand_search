"""Run the complete offline evidence loop against a temporary database."""

from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import create_app  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_smoke() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pain-radar-smoke-") as directory:
        database_path = (Path(directory) / "smoke.db").as_posix()
        settings = Settings(
            app_env="test",
            app_secret_key="smoke-test-only-secret",
            database_url=f"sqlite+pysqlite:///{database_path}",
            redis_url="",
            allowed_hosts="testserver",
            task_execution_mode="inline",
            store_full_page_text=False,
        )
        application = create_app(settings)
        Base.metadata.create_all(application.state.db.engine)
        with TestClient(application) as client:
            demo_response = client.post("/api/v1/research-jobs/demo")
            require(demo_response.status_code == 200, demo_response.text)
            job = demo_response.json()["job"]
            require(job["status"] == "completed", "demo job did not complete")
            require(job["discovered_source_count"] == 30, "unexpected source count")
            require(job["extracted_pain_point_count"] >= 30, "not enough pain points")

            listing_response = client.get(
                "/api/v1/pain-points",
                params={"page": 1, "page_size": 5, "sort_by": "evidence_score"},
            )
            require(listing_response.status_code == 200, listing_response.text)
            listing = listing_response.json()
            require(listing["total"] >= 30, "pain-point total is too small")
            require(len(listing["items"]) == 5, "server pagination was not applied")

            detail_response = client.get(f"/api/v1/pain-points/{listing['items'][0]['id']}")
            require(detail_response.status_code == 200, detail_response.text)
            detail = detail_response.json()
            require(bool(detail["evidences"]), "pain point has no evidence")
            require(
                {score["score_type"] for score in detail["scores"]}
                == {"evidence", "commercial", "coverage"},
                "score dimensions are not kept separate",
            )
            first_evidence = detail["evidences"][0]
            require(
                str(first_evidence["source_url_snapshot"]).startswith("https://"),
                "evidence source URL is not HTTP(S)",
            )

            all_items_response = client.get(
                "/api/v1/pain-points",
                params={"page": 1, "page_size": 100},
            )
            require(all_items_response.status_code == 200, all_items_response.text)
            all_items = all_items_response.json()["items"]
            require(len(all_items) >= 30, "full offline pain-point set is incomplete")
            evidence_records = 0
            for item in all_items:
                item_detail_response = client.get(f"/api/v1/pain-points/{item['id']}")
                require(item_detail_response.status_code == 200, item_detail_response.text)
                item_detail = item_detail_response.json()
                require(bool(item_detail["evidences"]), "pain point has no persisted evidence")
                evidence_records += len(item_detail["evidences"])

            csv_response = client.post("/api/v1/exports/pain-points", json={"format": "csv"})
            require(csv_response.status_code == 200, csv_response.text)
            rows = list(csv.DictReader(io.StringIO(csv_response.text)))
            require(len(rows) >= 30, "CSV export is incomplete")
            require(bool(rows[0]["primary_source_url"]), "CSV lost source provenance")

            json_response = client.post("/api/v1/exports/pain-points", json={"format": "json"})
            require(json_response.status_code == 200, json_response.text)
            exported = json.loads(json_response.text)
            require(exported["schema_version"] == "1.0", "JSON schema version changed")
            require(bool(exported["items"]), "JSON export has no items")

            markdown_response = client.post(
                "/api/v1/exports/pain-points", json={"format": "markdown"}
            )
            require(markdown_response.status_code == 200, markdown_response.text)
            require(
                "https://example.com/mock/" in markdown_response.text,
                "Markdown export lost evidence links",
            )

            return {
                "job_id": job["id"],
                "sources": job["discovered_source_count"],
                "pain_points": job["extracted_pain_point_count"],
                "listing_total": listing["total"],
                "evidence_records": evidence_records,
                "exports": ["csv", "json", "markdown"],
                "status": "passed",
            }


if __name__ == "__main__":
    print(json.dumps(run_smoke(), ensure_ascii=False, indent=2))
