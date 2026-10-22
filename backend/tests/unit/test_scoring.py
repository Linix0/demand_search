"""Deterministic score formula and cap tests."""

from __future__ import annotations

import pytest

from app.services.scoring import (
    CommercialOpportunityInput,
    CoverageInput,
    EvidenceConfidenceInput,
    ScoreDimension,
    calculate_commercial_opportunity,
    calculate_coverage,
    calculate_evidence_confidence,
    calculate_score,
)


def perfect_evidence(**overrides: object) -> EvidenceConfidenceInput:
    values = {
        "source_traceability": 5.0,
        "quote_verifiability": 5.0,
        "directness": 5.0,
        "independent_source_count": 5.0,
        "problem_specificity": 5.0,
        "observed_behavior": 5.0,
        "recency": 5.0,
    }
    values.update(overrides)
    return EvidenceConfidenceInput(**values)  # type: ignore[arg-type]


def perfect_commercial(**overrides: object) -> CommercialOpportunityInput:
    values = {
        "pain_severity": 5.0,
        "frequency": 5.0,
        "payment_willingness": 5.0,
        "target_user_reachability": 5.0,
        "indie_feasibility": 5.0,
        "competitive_gap": 5.0,
        "market_sustainability": 5.0,
        "has_payment_evidence": True,
    }
    values.update(overrides)
    return CommercialOpportunityInput(**values)  # type: ignore[arg-type]


def test_perfect_dimensions_produce_100() -> None:
    assert calculate_evidence_confidence(perfect_evidence()).total == 100.0
    assert calculate_commercial_opportunity(perfect_commercial()).total == 100.0


def test_no_source_url_forces_zero() -> None:
    result = calculate_evidence_confidence(perfect_evidence(has_source_url=False))

    assert result.total == 0.0
    assert result.caps_applied == ("no_source_url",)


def test_snippet_only_caps_evidence_at_55() -> None:
    result = calculate_evidence_confidence(perfect_evidence(snippet_only=True))

    assert result.total == 55.0
    assert "snippet_only_max_55" in result.caps_applied


def test_unverified_quote_caps_evidence_at_60() -> None:
    result = calculate_evidence_confidence(perfect_evidence(quote_verified=False))

    assert result.total == 60.0
    assert "unverified_quote_max_60" in result.caps_applied


def test_single_identity_caps_independence_dimension() -> None:
    result = calculate_evidence_confidence(perfect_evidence(single_thread_or_author=True))

    assert result.total == 88.0
    assert "single_identity_independence_max_1" in result.caps_applied


def test_no_payment_evidence_caps_commercial_dimension() -> None:
    result = calculate_commercial_opportunity(perfect_commercial(has_payment_evidence=False))

    assert result.total == 88.0


def test_missing_target_segment_caps_reachability() -> None:
    result = calculate_commercial_opportunity(perfect_commercial(target_user_defined=False))

    assert result.total == 91.0


def test_coverage_uses_independent_weights() -> None:
    result = calculate_coverage(
        CoverageInput(
            independent_sources=5,
            source_type_diversity=4,
            domain_diversity=3,
            time_coverage=2,
            target_user_clarity=1,
            competitor_research_completeness=0,
            interview_completion=5,
        )
    )

    assert result.total == 66.0
    assert result.score_type == "coverage"


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError):
        calculate_score(
            "test",
            (
                ScoreDimension("one", 0.5, 5, "First"),
                ScoreDimension("two", 0.2, 5, "Second"),
            ),
        )
