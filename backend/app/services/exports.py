"""Evidence-preserving CSV, JSON, and Markdown export generation."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.pain_point import PainPoint, PainPointEvidence, PainPointStatus
from app.services.exporting import render_csv

CSV_FIELDS = (
    "pain_point_id",
    "pain_statement",
    "status",
    "primary_category",
    "tags",
    "user_segment",
    "context",
    "current_workaround",
    "evidence_confidence_score",
    "commercial_opportunity_score",
    "coverage_score",
    "score_version",
    "distinct_source_count",
    "payment_signal_summary",
    "primary_source_url",
    "all_source_urls",
    "evidence_quotes",
    "source_published_at",
    "collected_at",
    "content_completeness",
    "quote_match_status",
    "root_cause_hypotheses",
    "competitor_urls",
    "next_validation_action",
)


@dataclass(frozen=True, slots=True)
class ExportPayload:
    filename: str
    media_type: str
    content: str
    row_count: int


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _load_pain_points(
    session: Session,
    *,
    job_id: uuid.UUID | None,
    status: PainPointStatus | None,
    max_items: int,
) -> list[PainPoint]:
    conditions: list[Any] = []
    if job_id is not None:
        conditions.append(PainPoint.created_from_job_id == job_id)
    if status is not None:
        conditions.append(PainPoint.status == status)
    statement = (
        select(PainPoint)
        .where(*conditions)
        .options(
            selectinload(PainPoint.evidences).selectinload(PainPointEvidence.source_item),
            selectinload(PainPoint.scores),
        )
        .order_by(
            PainPoint.evidence_confidence_score.desc(),
            PainPoint.commercial_opportunity_score.desc(),
            PainPoint.created_at.desc(),
        )
        .limit(max_items)
    )
    return list(session.scalars(statement).unique())


def _to_row(pain_point: PainPoint) -> dict[str, Any]:
    evidences = pain_point.evidences
    source_urls = _unique([item.source_url_snapshot for item in evidences])
    published_values = [
        item.source_published_at_snapshot.isoformat()
        for item in evidences
        if item.source_published_at_snapshot is not None
    ]
    competitor_urls = [
        str(item.get("url", ""))
        for item in pain_point.competitor_summary
        if isinstance(item, dict) and item.get("url")
    ]
    return {
        "pain_point_id": str(pain_point.id),
        "pain_statement": pain_point.canonical_statement,
        "status": pain_point.status.value,
        "primary_category": pain_point.category.code if pain_point.category else "",
        "tags": ",".join(pain_point.pain_type_tags),
        "user_segment": pain_point.user_segment,
        "context": pain_point.context,
        "current_workaround": pain_point.current_workaround,
        "evidence_confidence_score": f"{pain_point.evidence_confidence_score:.1f}",
        "commercial_opportunity_score": f"{pain_point.commercial_opportunity_score:.1f}",
        "coverage_score": f"{pain_point.coverage_score:.1f}",
        "score_version": pain_point.score_version,
        "distinct_source_count": pain_point.distinct_source_count,
        "payment_signal_summary": pain_point.payment_signal_summary,
        "primary_source_url": source_urls[0] if source_urls else "",
        "all_source_urls": "\n".join(source_urls),
        "evidence_quotes": "\n---\n".join(item.evidence_quote for item in evidences),
        "source_published_at": "\n".join(published_values),
        "collected_at": _iso(evidences[0].collected_at_snapshot) if evidences else "",
        "content_completeness": ",".join(
            _unique([item.source_item.content_completeness.value for item in evidences])
        ),
        "quote_match_status": ",".join(
            _unique([item.quote_match_status.value for item in evidences])
        ),
        "root_cause_hypotheses": json.dumps(pain_point.root_cause_hypotheses, ensure_ascii=False),
        "competitor_urls": "\n".join(competitor_urls),
        "next_validation_action": pain_point.validation_next_step,
    }


def _markdown_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "\\|")
        .replace("\r", " ")
    )


def _markdown_link(url: str) -> str:
    safe_url = url.replace(" ", "%20").replace(")", "%29").replace("<", "%3C").replace(">", "%3E")
    return f"<{safe_url}>"


def _render_markdown(pain_points: list[PainPoint], generated_at: datetime) -> str:
    lines = [
        "# Industry Pain Radar Report",
        "",
        f"- Generated: {generated_at.isoformat()}",
        "- Scope: evidence-driven pain-point candidates retained in the local source pool.",
        "- Method: deterministic scoring (`scores-v1`) over persisted quotes and source metadata.",
        "- Limitation: scores are research signals, not market facts. Human review is required.",
        "",
    ]
    for index, pain_point in enumerate(pain_points, start=1):
        category = pain_point.category.name if pain_point.category else "Uncategorized"
        lines.extend(
            [
                f"## {index}. {_markdown_escape(pain_point.canonical_statement)}",
                "",
                f"- Status: `{pain_point.status.value}`",
                f"- Category: {_markdown_escape(category)}",
                f"- User segment: {_markdown_escape(pain_point.user_segment)}",
                f"- Evidence confidence: **{pain_point.evidence_confidence_score:.1f}** / 100",
                f"- Commercial opportunity: **{pain_point.commercial_opportunity_score:.1f}** "
                "/ 100",
                f"- Coverage: **{pain_point.coverage_score:.1f}** / 100 (sample sufficiency only)",
                f"- Distinct sources: {pain_point.distinct_source_count}",
                f"- Payment signal: "
                f"{_markdown_escape(pain_point.payment_signal_summary or 'none recorded')}",
                "",
                f"**Current workaround:** "
                f"{_markdown_escape(pain_point.current_workaround or 'unknown')}",
                "",
                "### Score explanations",
                "",
            ]
        )
        latest_by_type: dict[str, Any] = {}
        for score in sorted(pain_point.scores, key=lambda item: item.scored_at):
            latest_by_type[score.score_type.value] = score
        for score_type in ("evidence", "commercial", "coverage"):
            latest_score = latest_by_type.get(score_type)
            if latest_score is None:
                continue
            lines.append(
                f"- **{score_type.title()} {latest_score.total_score:.1f}** "
                f"(`{latest_score.scoring_version}`)"
            )
            for dimension in latest_score.dimension_scores:
                lines.append(
                    "  - "
                    f"`{dimension.get('code', '')}`: {dimension.get('raw_score', '')}/5, "
                    f"weight {dimension.get('weight', '')}: "
                    f"{_markdown_escape(str(dimension.get('rationale', '')))}"
                )
        lines.extend(["", "### Evidence", ""])
        if not pain_point.evidences:
            lines.append("- No evidence records. This item cannot be treated as a verified fact.")
        for evidence in pain_point.evidences:
            lines.extend(
                [
                    f"- Source: {_markdown_escape(evidence.source_item.source_name)} — "
                    f"{_markdown_link(evidence.source_url_snapshot)}",
                    f"  - Title: "
                    f"{_markdown_escape(evidence.source_item.source_title or 'unknown')}",
                    f"  - Quote: > {_markdown_escape(evidence.evidence_quote)}",
                    f"  - Match: `{evidence.quote_match_status.value}`; completeness: "
                    f"`{evidence.source_item.content_completeness.value}`",
                    f"  - Published: {_iso(evidence.source_published_at_snapshot) or 'unknown'}; "
                    f"collected: {_iso(evidence.collected_at_snapshot)}",
                ]
            )
        lines.extend(
            [
                "",
                f"**Next validation step:** {_markdown_escape(pain_point.validation_next_step)}",
                "",
            ]
        )
    return "\n".join(lines)


def build_export(
    session: Session,
    *,
    export_format: str,
    job_id: uuid.UUID | None = None,
    status: PainPointStatus | None = None,
    max_items: int = 1_000,
) -> ExportPayload:
    pain_points = _load_pain_points(session, job_id=job_id, status=status, max_items=max_items)
    rows = [_to_row(item) for item in pain_points]
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if export_format == "csv":
        return ExportPayload(
            filename=f"pain-points-{stamp}.csv",
            media_type="text/csv; charset=utf-8",
            content=render_csv(rows, CSV_FIELDS),
            row_count=len(rows),
        )
    if export_format == "json":
        payload = {
            "schema_version": "1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "scoring_version": "scores-v1",
            "limitations": [
                "Scores are research signals, not market facts.",
                "Human review is required before treating a candidate as verified.",
            ],
            "items": rows,
        }
        return ExportPayload(
            filename=f"pain-points-{stamp}.json",
            media_type="application/json; charset=utf-8",
            content=json.dumps(payload, ensure_ascii=False, indent=2),
            row_count=len(rows),
        )
    return ExportPayload(
        filename=f"pain-points-{stamp}.md",
        media_type="text/markdown; charset=utf-8",
        content=_render_markdown(pain_points, datetime.now(UTC)),
        row_count=len(rows),
    )
