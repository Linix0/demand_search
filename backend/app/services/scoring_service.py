"""Apply versioned deterministic scores and preserve append-only history."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.pain_point import (
    EvidenceRole,
    PainPoint,
    PainPointScore,
    QuoteMatchStatus,
    ScoreType,
)
from app.services.evidence import normalize_evidence_text
from app.services.scoring import (
    CommercialOpportunityInput,
    CoverageInput,
    EvidenceConfidenceInput,
    ScoreResult,
    calculate_commercial_opportunity,
    calculate_coverage,
    calculate_evidence_confidence,
)


def _quote_raw_score(status: QuoteMatchStatus) -> float:
    return {
        QuoteMatchStatus.EXACT_MATCH: 5.0,
        QuoteMatchStatus.NORMALIZED_MATCH: 4.0,
        QuoteMatchStatus.SNIPPET_ONLY: 2.0,
        QuoteMatchStatus.NOT_FOUND: 0.0,
    }[status]


def _recency_score(published_at: datetime | None, now: datetime) -> float:
    if published_at is None:
        return 0.0
    value = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
    days = max(0, (now - value).days)
    if days <= 30:
        return 5.0
    if days <= 90:
        return 4.0
    if days <= 365:
        return 3.0
    if days <= 1_095:
        return 1.0
    return 0.0


def _dimension_payload(result: ScoreResult) -> list[dict[str, Any]]:
    return [
        {
            "code": item.code,
            "weight": item.weight,
            "raw_score": item.raw_score,
            "rationale": item.rationale,
        }
        for item in result.dimensions
    ]


def recalculate_pain_point(session: Session, pain_point: PainPoint) -> None:
    """Recalculate all three score types from persisted evidence only."""

    evidences = [
        item
        for item in pain_point.evidences
        if item.quote_match_status != QuoteMatchStatus.NOT_FOUND
    ]
    now = datetime.now(UTC)
    if not evidences:
        evidence_result = calculate_evidence_confidence(
            EvidenceConfidenceInput(0, 0, 0, 0, 0, 0, 0, has_source_url=False)
        )
        commercial_result = calculate_commercial_opportunity(
            CommercialOpportunityInput(0, 0, 0, 0, 0, 0, 0, False, False)
        )
        coverage_result = calculate_coverage(CoverageInput(0, 0, 0, 0, 0, 0, 0))
    else:
        strongest = max(evidences, key=lambda item: _quote_raw_score(item.quote_match_status))
        source = strongest.source_item
        unique_sources = {item.source_item_id for item in evidences}
        unique_authors = {
            item.author_independence_key
            or item.source_item.source_author_hash
            or str(item.source_item_id)
            for item in evidences
        }
        single_identity = len(unique_authors) <= 1
        snippet_only = all(
            item.quote_match_status == QuoteMatchStatus.SNIPPET_ONLY for item in evidences
        )
        quote_verified = strongest.quote_match_status in {
            QuoteMatchStatus.EXACT_MATCH,
            QuoteMatchStatus.NORMALIZED_MATCH,
        }
        text = (
            f"{source.source_title} {source.content_text or source.content_excerpt or ''}".lower()
        )
        observed_behavior = (
            4.0
            if any(
                marker in text
                for marker in ("spreadsheet", "manual", "copy", "reconcile", "three tools")
            )
            else 2.0
        )
        evidence_result = calculate_evidence_confidence(
            EvidenceConfidenceInput(
                source_traceability=5.0 if source.source_url else 0.0,
                quote_verifiability=_quote_raw_score(strongest.quote_match_status),
                directness=4.0 if source.source_trust_tier.startswith(("A", "B")) else 2.0,
                independent_source_count=float(min(len(unique_sources), 8)),
                problem_specificity=3.0,
                observed_behavior=observed_behavior,
                recency=_recency_score(source.published_at, now),
                has_source_url=bool(source.source_url),
                snippet_only=snippet_only,
                quote_verified=quote_verified,
                single_thread_or_author=single_identity,
            )
        )

        has_payment = any(item.evidence_role == EvidenceRole.PAYMENT_SIGNAL for item in evidences)
        target_defined = pain_point.user_segment not in {"", "unknown"}
        commercial_result = calculate_commercial_opportunity(
            CommercialOpportunityInput(
                pain_severity=4.0 if observed_behavior >= 4 else 3.0,
                frequency=3.0,
                payment_willingness=4.0 if has_payment else 1.0,
                target_user_reachability=3.0 if target_defined else 1.0,
                indie_feasibility=4.0,
                competitive_gap=3.0,
                market_sustainability=3.0,
                has_payment_evidence=has_payment,
                target_user_defined=target_defined,
            )
        )
        coverage_result = calculate_coverage(
            CoverageInput(
                independent_sources=float(min(len(unique_sources), 5)),
                source_type_diversity=float(
                    min(len({item.source_item.source_trust_tier for item in evidences}), 5)
                ),
                domain_diversity=float(
                    min(len({item.source_item.source_domain for item in evidences}), 5)
                ),
                time_coverage=3.0,
                target_user_clarity=3.0 if target_defined else 1.0,
                competitor_research_completeness=0.0,
                interview_completion=0.0,
            )
        )

    pain_point.evidence_confidence_score = evidence_result.total
    pain_point.commercial_opportunity_score = commercial_result.total
    pain_point.coverage_score = coverage_result.total
    pain_point.score_version = evidence_result.version
    pain_point.distinct_source_count = len({item.source_item_id for item in evidences})
    pain_point.distinct_thread_count = pain_point.distinct_source_count
    if evidences:
        pain_point.last_evidence_at = max(item.collected_at_snapshot for item in evidences)
        pain_point.payment_signal_summary = (
            "Explicit budget or purchase signal found in the cited source."
            if any(item.evidence_role == EvidenceRole.PAYMENT_SIGNAL for item in evidences)
            else ""
        )

    evidence_ids = [str(item.id) for item in evidences]
    scored_at = datetime.now(UTC)
    for score_type, result in (
        (ScoreType.EVIDENCE, evidence_result),
        (ScoreType.COMMERCIAL, commercial_result),
        (ScoreType.COVERAGE, coverage_result),
    ):
        session.add(
            PainPointScore(
                pain_point_id=pain_point.id,
                score_type=score_type,
                scoring_version=result.version,
                total_score=result.total,
                dimension_scores=_dimension_payload(result),
                evidence_ids_used=evidence_ids,
                calculation_details={
                    "formula": "sum(dimension_score / 5 * weight) * 100",
                    "distinct_source_count": pain_point.distinct_source_count,
                    "evidence_quote_statuses": [
                        item.quote_match_status.value for item in evidences
                    ],
                },
                rule_adjustments=list(result.caps_applied),
                scored_at=scored_at,
            )
        )
    session.flush()


def normalized_statement_key(statement: str) -> str:
    return normalize_evidence_text(statement).lower()
