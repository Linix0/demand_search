"""Bounded offline-first research pipeline from query to scored evidence."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlsplit

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.pain_point import (
    EvidenceRole,
    EvidenceType,
    ManualVerificationStatus,
    PainPoint,
    PainPointEvidence,
    PainPointStatus,
    QuoteMatchStatus,
)
from app.models.research import QueryStatus, SearchQuery
from app.models.research_job import JobStage, JobStatus, ResearchJob
from app.models.source import (
    ContentCompleteness,
    RetrievalMethod,
    SourceItem,
    SourceTrustTier,
    UrlStatus,
)
from app.models.taxonomy import TaxonomyCategory, TaxonomyTag
from app.providers.llm.base import ExtractionRequest
from app.providers.llm.mock import MockLLMProvider
from app.providers.search.base import SearchRequest, SearchResult
from app.providers.search.mock import MockSearchProvider
from app.repositories.sources import find_source_by_canonical_url, find_source_by_external_id
from app.services.evidence import normalize_evidence_text, verify_evidence_quote
from app.services.jobs import add_job_log
from app.services.scoring_service import recalculate_pain_point
from app.services.url_safety import validate_outbound_url

logger = structlog.get_logger(__name__)

QUERY_TEMPLATES = (
    "{keyword} repetitive manual workflow",
    "{keyword} current workaround spreadsheet",
    "{keyword} too expensive small team",
    "{keyword} missing integration feature",
    "{keyword} frustrating workflow problem",
)


class CandidatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_item_id: str
    pain_statement: str = Field(min_length=10, max_length=2_000)
    user_segment: str = Field(default="unknown", max_length=160)
    context: str = Field(default="", max_length=2_000)
    problem_detail: str = Field(default="", max_length=5_000)
    current_workaround: str = Field(default="", max_length=3_000)
    payment_signal: Literal["none", "explicit", "inferred_only", "unknown"] = "none"
    evidence_quote: str = Field(min_length=20, max_length=500)
    evidence_start_offset: int | None = None
    evidence_end_offset: int | None = None
    candidate_type: str = "first_person_pain"
    tags: list[str] = Field(default_factory=list, max_length=20)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)


def _build_queries(config: dict[str, Any]) -> list[tuple[str, str]]:
    keywords = [str(value) for value in config.get("seed_keywords", [])]
    max_queries = int(config.get("max_queries", 10))
    queries: list[tuple[str, str]] = []
    for keyword in keywords:
        for template in QUERY_TEMPLATES:
            if len(queries) >= max_queries:
                return queries
            intent = template.split(" ", 1)[1].replace(" ", "_")
            queries.append((template.format(keyword=keyword), intent[:64]))
    return queries


def _completeness(result: SearchResult) -> ContentCompleteness:
    raw_value = str(result.metadata.get("content_completeness", "snippet_only"))
    try:
        return ContentCompleteness(raw_value)
    except ValueError:
        return ContentCompleteness.SNIPPET_ONLY


def _trust_tier(result: SearchResult, completeness: ContentCompleteness) -> SourceTrustTier:
    raw_value = str(result.metadata.get("trust_tier", ""))
    try:
        return SourceTrustTier(raw_value)
    except ValueError:
        return {
            ContentCompleteness.FULL_PUBLIC_CONTENT: SourceTrustTier.A_PRIMARY_USER_REPORT,
            ContentCompleteness.PARTIAL_CONTENT: SourceTrustTier.C_SECONDARY_REVIEW,
            ContentCompleteness.SNIPPET_ONLY: SourceTrustTier.D_SEARCH_SNIPPET,
            ContentCompleteness.METADATA_ONLY: SourceTrustTier.D_SEARCH_SNIPPET,
        }[completeness]


def _persist_source(
    session: Session,
    *,
    job: ResearchJob,
    result: SearchResult,
    settings: Settings,
    max_total_items: int,
) -> tuple[SourceItem | None, bool]:
    if job.discovered_source_count >= max_total_items:
        return None, False
    try:
        canonical_url = validate_outbound_url(
            result.url,
            allowed_ports=settings.allowed_ports,
            require_public_dns=False,
        )
    except Exception as exc:
        add_job_log(
            session,
            job,
            stage="searching",
            level="warning",
            message="Skipped a search result that failed URL safety validation.",
            detail={"reason": type(exc).__name__, "provider": result.provider_code},
        )
        return None, False

    existing = find_source_by_external_id(session, result.provider_code, result.external_id)
    if existing is None:
        existing = find_source_by_canonical_url(session, canonical_url)
    if existing is not None:
        return None, True

    completeness = _completeness(result)
    tier = _trust_tier(result, completeness)
    collected_at = datetime.now(UTC)
    title = result.title.strip()[:1_000]
    snippet = result.snippet.strip()[:2_000]
    source_text = f"{title}\n{snippet}".strip()
    author = result.author or result.metadata.get("author")
    author_hash = hashlib.sha256(str(author).encode("utf-8")).hexdigest() if author else None
    hostname = (urlsplit(canonical_url).hostname or "").lower()
    source = SourceItem(
        research_job_id=job.id,
        provider_code=result.provider_code,
        external_id=result.external_id,
        source_name="Mock Search" if result.provider_code == "mock" else result.provider_code,
        source_domain=hostname,
        source_url=result.url,
        canonical_url=canonical_url,
        final_url=None,
        source_title=title,
        source_author_hash=author_hash,
        published_at=result.published_at,
        collected_at=collected_at,
        content_text=source_text if completeness != ContentCompleteness.SNIPPET_ONLY else None,
        content_excerpt=snippet,
        content_hash=hashlib.sha256(
            normalize_evidence_text(source_text).encode("utf-8")
        ).hexdigest(),
        content_completeness=completeness,
        url_status=UrlStatus.UNCHECKED,
        retrieval_method=RetrievalMethod.SEARCH_API,
        raw_metadata={
            "fixture": bool(result.metadata.get("fixture")),
            "query_source": "mock_search",
        },
        relevance_score={
            ContentCompleteness.FULL_PUBLIC_CONTENT: 75,
            ContentCompleteness.PARTIAL_CONTENT: 60,
            ContentCompleteness.SNIPPET_ONLY: 45,
            ContentCompleteness.METADATA_ONLY: 35,
        }[completeness],
        source_trust_tier=tier,
        is_duplicate=False,
        retention_until=datetime.now(UTC) + timedelta(days=settings.default_retention_days),
    )
    session.add(source)
    session.flush()
    job.discovered_source_count += 1
    return source, False


def _extract_candidate(
    *,
    source: SourceItem,
    llm: MockLLMProvider,
) -> CandidatePayload | None:
    source_text = source.content_text or (
        f"{source.source_title}\n{source.content_excerpt or ''}".strip()
    )
    response = llm.extract_candidates(
        ExtractionRequest(source_item_id=str(source.id), source_text=source_text)
    )
    if response.source_item_id != str(source.id):
        raise ValueError("LLM response attempted to bind a different source item")
    if not response.candidates:
        return None
    try:
        candidate = CandidatePayload.model_validate(response.candidates[0])
    except ValidationError as exc:
        raise ValueError("LLM candidate failed strict schema validation") from exc
    if candidate.source_item_id != str(source.id):
        raise ValueError("LLM candidate supplied a fabricated source item id")
    return candidate


def _evidence_type(candidate: CandidatePayload) -> EvidenceType:
    try:
        return EvidenceType(candidate.candidate_type)
    except ValueError:
        return EvidenceType.OTHER


def run_research_job(session: Session, job: ResearchJob, settings: Settings) -> ResearchJob:
    """Run the Mock-first bounded pipeline and persist every stage outcome."""

    if job.status in {JobStatus.CANCELLED, JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ERRORS}:
        return job
    if settings.search_provider_default != "mock" or settings.llm_provider != "mock":
        raise ValueError("Phase 1 supports only the Mock search and LLM providers")

    search_provider = MockSearchProvider()
    llm_provider = MockLLMProvider()
    config = job.config_json
    max_results = int(config.get("max_results_per_query", 3))
    max_total_items = min(int(config.get("max_total_items", 60)), settings.default_job_max_sources)
    errors: list[str] = []
    verified_evidence_count = 0

    job.status = JobStatus.RUNNING
    job.stage = JobStage.QUERY_PLANNING
    job.started_at = job.started_at or datetime.now(UTC)
    job.error_summary = None
    job.progress_percent = 5
    add_job_log(session, job, stage="query_planning", message="Research job started.")
    session.commit()

    try:
        queries = _build_queries(config)
        if not queries:
            raise ValueError("No search queries could be planned")
        query_rows: list[SearchQuery] = []
        for priority, (query_text, intent) in enumerate(queries):
            row = SearchQuery(
                research_job_id=job.id,
                provider_code=search_provider.code,
                query_text=query_text,
                intent_type=intent,
                language=str(config.get("languages", ["zh-CN"])[0]),
                priority=priority,
                status=QueryStatus.PENDING,
            )
            session.add(row)
            query_rows.append(row)
        job.planned_query_count = len(query_rows)
        job.progress_percent = 12
        add_job_log(
            session,
            job,
            stage="query_planning",
            message="Planned bounded search queries.",
            detail={"query_count": len(query_rows)},
        )
        session.commit()

        job.stage = JobStage.SEARCHING
        job.progress_percent = 18
        session.commit()
        duplicate_count = 0
        for query_row in query_rows:
            session.refresh(job)
            if job.status in {JobStatus.PAUSED, JobStatus.CANCELLED}:
                add_job_log(
                    session,
                    job,
                    stage="searching",
                    message="Job stopped before the next query.",
                )
                session.commit()
                return job
            query_row.status = QueryStatus.RUNNING
            try:
                results = search_provider.search(
                    SearchRequest(
                        query=query_row.query_text,
                        language=query_row.language,
                        limit=max_results,
                        date_from=job.date_from,
                        date_to=job.date_to,
                    )
                )
            except Exception as exc:
                query_row.status = QueryStatus.FAILED
                query_row.error_summary = type(exc).__name__
                errors.append(f"query_failed:{query_row.intent_type}")
                continue

            query_row.result_count = len(results)
            query_row.status = QueryStatus.COMPLETED
            query_row.executed_at = datetime.now(UTC)
            job.processed_query_count += 1
            for result in results:
                source, was_duplicate = _persist_source(
                    session,
                    job=job,
                    result=result,
                    settings=settings,
                    max_total_items=max_total_items,
                )
                duplicate_count += int(was_duplicate)
                if source is None:
                    continue
                try:
                    candidate = _extract_candidate(source=source, llm=llm_provider)
                except Exception as exc:
                    errors.append(f"extraction_failed:{source.id}")
                    add_job_log(
                        session,
                        job,
                        stage="extracting",
                        level="warning",
                        message="Candidate extraction was rejected; source retained.",
                        detail={"reason": type(exc).__name__, "source_id": str(source.id)},
                    )
                    continue
                if candidate is None:
                    continue

                verification = verify_evidence_quote(
                    source.content_text,
                    candidate.evidence_quote,
                    content_completeness=source.content_completeness.value,
                )
                category_code = str(config.get("primary_categories", ["other"])[0])
                category = session.scalar(
                    select(TaxonomyCategory).where(TaxonomyCategory.code == category_code)
                )
                known_tags = set(session.scalars(select(TaxonomyTag.code)))
                tags = [tag for tag in candidate.tags if tag in known_tags][:20]
                payment_explicit = candidate.payment_signal == "explicit"
                statement = candidate.pain_statement.strip()
                existing_statement = session.scalar(
                    select(PainPoint.id).where(
                        PainPoint.created_from_job_id == job.id,
                        PainPoint.canonical_statement == statement,
                    )
                )
                if existing_statement is not None:
                    errors.append(f"duplicate_candidate:{source.id}")
                    continue

                pain_point = PainPoint(
                    workspace_id=job.workspace_id,
                    created_from_job_id=job.id,
                    primary_category_id=category.id if category else None,
                    canonical_statement=statement,
                    user_segment=candidate.user_segment or "unknown",
                    context=candidate.context,
                    problem_detail=candidate.problem_detail,
                    current_workaround=candidate.current_workaround,
                    current_solution_gap="",
                    pain_type_tags=tags,
                    status=(
                        PainPointStatus.NEEDS_REVIEW
                        if verification.is_verified
                        else PainPointStatus.HYPOTHESIS
                    ),
                    payment_signal_summary="",
                    root_cause_hypotheses=[],
                    competitor_summary=[],
                    validation_next_step=(
                        "Contact a target user and ask them to walk through the current workflow."
                    ),
                )
                session.add(pain_point)
                session.flush()

                evidence_status = QuoteMatchStatus(verification.status.value)
                evidence = PainPointEvidence(
                    pain_point_id=pain_point.id,
                    source_item_id=source.id,
                    evidence_quote=candidate.evidence_quote,
                    evidence_quote_normalized=verification.normalized_quote,
                    quote_match_status=evidence_status,
                    evidence_type=_evidence_type(candidate),
                    evidence_role=(
                        EvidenceRole.PAYMENT_SIGNAL if payment_explicit else EvidenceRole.SUPPORTING
                    ),
                    evidence_strength_score={
                        QuoteMatchStatus.EXACT_MATCH: 80.0,
                        QuoteMatchStatus.NORMALIZED_MATCH: 60.0,
                        QuoteMatchStatus.SNIPPET_ONLY: 45.0,
                        QuoteMatchStatus.NOT_FOUND: 20.0,
                    }[evidence_status],
                    source_url_snapshot=source.canonical_url,
                    target_url=source.canonical_url,
                    related_target_urls=[],
                    source_published_at_snapshot=source.published_at,
                    collected_at_snapshot=source.collected_at,
                    author_independence_key=source.source_author_hash,
                    manual_verification_status=ManualVerificationStatus.UNREVIEWED,
                    manual_note="",
                )
                pain_point.evidences.append(evidence)
                session.flush()
                recalculate_pain_point(session, pain_point)
                job.extracted_pain_point_count += 1
                if verification.is_verified:
                    verified_evidence_count += 1

            job.processed_source_count = job.discovered_source_count
            progress_span = max(1, job.planned_query_count)
            job.progress_percent = min(85, 18 + int(60 * job.processed_query_count / progress_span))
            session.commit()

        job.stage = JobStage.COMPLETED
        job.progress_percent = 100
        job.verified_evidence_count = verified_evidence_count
        job.finished_at = datetime.now(UTC)
        job.status = JobStatus.COMPLETED_WITH_ERRORS if errors else JobStatus.COMPLETED
        job.error_summary = f"{len(errors)} non-fatal item(s) were skipped." if errors else None
        add_job_log(
            session,
            job,
            stage="completed",
            level="warning" if errors else "info",
            message=(
                "Research job completed with recoverable item errors."
                if errors
                else "Research job completed."
            ),
            detail={
                "sources": job.discovered_source_count,
                "pain_points": job.extracted_pain_point_count,
                "duplicates_skipped": duplicate_count,
                "non_fatal_errors": len(errors),
            },
        )
        session.commit()
        session.refresh(job)
        return job
    except Exception as exc:
        session.rollback()
        job = session.get(ResearchJob, job.id) or job
        job.status = JobStatus.FAILED
        job.error_summary = "Research pipeline failed; inspect job logs."
        job.finished_at = datetime.now(UTC)
        add_job_log(
            session,
            job,
            stage=job.stage.value,
            level="error",
            message="Research pipeline failed.",
            detail={"error_type": type(exc).__name__},
        )
        session.commit()
        logger.exception("research_job_failed", job_id=str(job.id), error_type=type(exc).__name__)
        return job
