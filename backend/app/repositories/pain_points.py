"""Filtered, sortable pain-point queries; no full-table API responses."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.pain_point import (
    PainPoint,
    PainPointEvidence,
    PainPointStatus,
    QuoteMatchStatus,
)
from app.models.taxonomy import TaxonomyCategory

SORT_COLUMNS: dict[str, Any] = {
    "created_at": PainPoint.created_at,
    "updated_at": PainPoint.updated_at,
    "evidence_score": PainPoint.evidence_confidence_score,
    "commercial_score": PainPoint.commercial_opportunity_score,
    "coverage_score": PainPoint.coverage_score,
    "last_evidence_at": PainPoint.last_evidence_at,
}


def get_pain_point(
    session: Session, pain_point_id: uuid.UUID, *, detail: bool = False
) -> PainPoint | None:
    statement = select(PainPoint).where(PainPoint.id == pain_point_id)
    if detail:
        statement = statement.options(
            selectinload(PainPoint.evidences).selectinload(PainPointEvidence.source_item),
            selectinload(PainPoint.scores),
        )
    return session.scalar(statement)


def list_pain_points(
    session: Session,
    *,
    page: int,
    page_size: int,
    statuses: list[PainPointStatus] | None = None,
    category_code: str | None = None,
    job_id: uuid.UUID | None = None,
    min_evidence_score: float | None = None,
    min_commercial_score: float | None = None,
    min_coverage_score: float | None = None,
    has_verified_evidence: bool | None = None,
    has_payment_signal: bool | None = None,
    query: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str = "evidence_score",
    sort_order: str = "desc",
) -> tuple[list[PainPoint], int]:
    conditions: list[Any] = []
    if statuses:
        conditions.append(PainPoint.status.in_(statuses))
    if category_code:
        conditions.append(TaxonomyCategory.code == category_code)
    if job_id is not None:
        conditions.append(PainPoint.created_from_job_id == job_id)
    if min_evidence_score is not None:
        conditions.append(PainPoint.evidence_confidence_score >= min_evidence_score)
    if min_commercial_score is not None:
        conditions.append(PainPoint.commercial_opportunity_score >= min_commercial_score)
    if min_coverage_score is not None:
        conditions.append(PainPoint.coverage_score >= min_coverage_score)
    if has_verified_evidence is True:
        conditions.append(
            exists().where(
                PainPointEvidence.pain_point_id == PainPoint.id,
                PainPointEvidence.quote_match_status.in_(
                    [QuoteMatchStatus.EXACT_MATCH, QuoteMatchStatus.NORMALIZED_MATCH]
                ),
            )
        )
    if has_verified_evidence is False:
        conditions.append(
            ~exists().where(
                PainPointEvidence.pain_point_id == PainPoint.id,
                PainPointEvidence.quote_match_status.in_(
                    [QuoteMatchStatus.EXACT_MATCH, QuoteMatchStatus.NORMALIZED_MATCH]
                ),
            )
        )
    if has_payment_signal is True:
        conditions.append(PainPoint.payment_signal_summary != "")
    if has_payment_signal is False:
        conditions.append(PainPoint.payment_signal_summary == "")
    if query:
        pattern = f"%{query.strip()}%"
        conditions.append(
            or_(
                PainPoint.canonical_statement.ilike(pattern),
                PainPoint.problem_detail.ilike(pattern),
                PainPoint.context.ilike(pattern),
            )
        )
    if date_from is not None:
        conditions.append(PainPoint.created_at >= date_from)
    if date_to is not None:
        conditions.append(PainPoint.created_at <= date_to)

    base = select(PainPoint).join(TaxonomyCategory, isouter=True).where(*conditions)
    total = (
        session.scalar(
            select(func.count())
            .select_from(PainPoint)
            .join(TaxonomyCategory, isouter=True)
            .where(*conditions)
        )
        or 0
    )

    sort_column = SORT_COLUMNS.get(sort_by, PainPoint.evidence_confidence_score)
    order = sort_column.desc() if sort_order.lower() != "asc" else sort_column.asc()
    statement = (
        base.order_by(order, PainPoint.created_at.desc(), PainPoint.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(session.scalars(statement).unique()), total
