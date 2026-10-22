"""Versioned, explainable scoring formulas separated by score type."""

from __future__ import annotations

from dataclasses import dataclass

SCORING_VERSION = "scores-v1"


@dataclass(frozen=True, slots=True)
class ScoreDimension:
    code: str
    weight: float
    raw_score: float
    rationale: str


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score_type: str
    total: float
    version: str
    dimensions: tuple[ScoreDimension, ...]
    caps_applied: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceConfidenceInput:
    source_traceability: float
    quote_verifiability: float
    directness: float
    independent_source_count: float
    problem_specificity: float
    observed_behavior: float
    recency: float
    has_source_url: bool = True
    snippet_only: bool = False
    quote_verified: bool = True
    single_thread_or_author: bool = False


@dataclass(frozen=True, slots=True)
class CommercialOpportunityInput:
    pain_severity: float
    frequency: float
    payment_willingness: float
    target_user_reachability: float
    indie_feasibility: float
    competitive_gap: float
    market_sustainability: float
    has_payment_evidence: bool = False
    target_user_defined: bool = True


@dataclass(frozen=True, slots=True)
class CoverageInput:
    independent_sources: float
    source_type_diversity: float
    domain_diversity: float
    time_coverage: float
    target_user_clarity: float
    competitor_research_completeness: float
    interview_completion: float


def _validate_dimension(dimension: ScoreDimension) -> None:
    if not 0 <= dimension.raw_score <= 5:
        raise ValueError(f"{dimension.code} must be within 0-5")
    if not 0 <= dimension.weight <= 1:
        raise ValueError(f"{dimension.code} weight must be within 0-1")
    if not dimension.rationale.strip():
        raise ValueError(f"{dimension.code} requires a rationale")


def calculate_score(
    score_type: str,
    dimensions: tuple[ScoreDimension, ...],
    *,
    version: str = SCORING_VERSION,
    total_cap: float | None = None,
    caps_applied: tuple[str, ...] = (),
) -> ScoreResult:
    """Calculate a 0-100 score from weighted 0-5 dimensions."""

    if not dimensions:
        raise ValueError("At least one score dimension is required")
    for dimension in dimensions:
        _validate_dimension(dimension)

    weight_sum = sum(dimension.weight for dimension in dimensions)
    if abs(weight_sum - 1.0) > 0.001:
        raise ValueError(f"Dimension weights must sum to 1.0; got {weight_sum:.3f}")

    total = round(
        sum(dimension.raw_score / 5 * dimension.weight * 100 for dimension in dimensions), 1
    )
    if total_cap is not None:
        total = min(total, total_cap)
    if not 0 <= total <= 100:
        raise ValueError("Final score must be within 0-100")

    return ScoreResult(
        score_type=score_type,
        total=total,
        version=version,
        dimensions=dimensions,
        caps_applied=caps_applied,
    )


def calculate_evidence_confidence(value: EvidenceConfidenceInput) -> ScoreResult:
    if not value.has_source_url:
        return ScoreResult(
            score_type="evidence",
            total=0.0,
            version=SCORING_VERSION,
            dimensions=(),
            caps_applied=("no_source_url",),
        )

    independence = (
        min(value.independent_source_count, 1.0)
        if value.single_thread_or_author
        else value.independent_source_count
    )
    dimensions = (
        ScoreDimension(
            "source_traceability",
            0.20,
            value.source_traceability,
            "Source URL and locator traceability",
        ),
        ScoreDimension(
            "quote_verifiability",
            0.20,
            value.quote_verifiability,
            "Quote is present in retrievable text",
        ),
        ScoreDimension("directness", 0.15, value.directness, "First-person vs secondary evidence"),
        ScoreDimension(
            "independent_source_count",
            0.15,
            independence,
            "Deduplicated independent source estimate",
        ),
        ScoreDimension(
            "problem_specificity",
            0.10,
            value.problem_specificity,
            "Task, obstacle, and context specificity",
        ),
        ScoreDimension(
            "observed_behavior", 0.10, value.observed_behavior, "Workaround or behavior evidence"
        ),
        ScoreDimension("recency", 0.10, value.recency, "Publication recency"),
    )

    caps: list[str] = []
    total_cap: float | None = None
    if value.snippet_only:
        total_cap = 55.0
        caps.append("snippet_only_max_55")
    if not value.quote_verified:
        total_cap = min(total_cap or 100.0, 60.0)
        caps.append("unverified_quote_max_60")
    if value.single_thread_or_author:
        caps.append("single_identity_independence_max_1")

    return calculate_score(
        "evidence",
        dimensions,
        total_cap=total_cap,
        caps_applied=tuple(caps),
    )


def calculate_commercial_opportunity(value: CommercialOpportunityInput) -> ScoreResult:
    payment = (
        min(value.payment_willingness, 2.0)
        if not value.has_payment_evidence
        else value.payment_willingness
    )
    reachability = (
        min(value.target_user_reachability, 2.0)
        if not value.target_user_defined
        else value.target_user_reachability
    )
    dims = (
        ScoreDimension(
            "pain_severity", 0.20, value.pain_severity, "Severity of impact or blockage"
        ),
        ScoreDimension("frequency", 0.15, value.frequency, "Observed repetition or duration"),
        ScoreDimension(
            "payment_willingness",
            0.20,
            payment,
            "Explicit payment, budget, or paid alternative evidence",
        ),
        ScoreDimension(
            "target_user_reachability",
            0.15,
            reachability,
            "Ability to identify and contact early users",
        ),
        ScoreDimension(
            "indie_feasibility",
            0.15,
            value.indie_feasibility,
            "2-6 week validation feasibility and risk",
        ),
        ScoreDimension(
            "competitive_gap", 0.10, value.competitive_gap, "Evidence-backed differentiation gap"
        ),
        ScoreDimension(
            "market_sustainability",
            0.05,
            value.market_sustainability,
            "Recurring value and delivery sustainability",
        ),
    )
    caps: list[str] = []
    if not value.has_payment_evidence:
        caps.append("no_payment_evidence_max_2")
    if not value.target_user_defined:
        caps.append("no_target_segment_max_2")
    return calculate_score("commercial", dims, caps_applied=tuple(caps))


def calculate_coverage(value: CoverageInput) -> ScoreResult:
    dims = (
        ScoreDimension(
            "independent_sources", 0.30, value.independent_sources, "Independent source coverage"
        ),
        ScoreDimension(
            "source_type_diversity", 0.20, value.source_type_diversity, "Diverse source types"
        ),
        ScoreDimension(
            "domain_diversity", 0.15, value.domain_diversity, "Diverse domains or communities"
        ),
        ScoreDimension("time_coverage", 0.10, value.time_coverage, "Time span coverage"),
        ScoreDimension(
            "target_user_clarity", 0.10, value.target_user_clarity, "Target user clarity"
        ),
        ScoreDimension(
            "competitor_research",
            0.10,
            value.competitor_research_completeness,
            "Competitor research completeness",
        ),
        ScoreDimension(
            "interview_completion",
            0.05,
            value.interview_completion,
            "Interview or direct-feedback completion",
        ),
    )
    return calculate_score("coverage", dims)
