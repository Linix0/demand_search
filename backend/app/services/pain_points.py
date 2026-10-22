"""Pain-point read models, review transitions, merge, and rescore rules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, UrlSafetyError
from app.models.pain_point import (
    Annotation,
    ManualVerificationStatus,
    PainPoint,
    PainPointStatus,
    QuoteMatchStatus,
)
from app.models.taxonomy import TaxonomyCategory
from app.repositories.pain_points import get_pain_point, list_pain_points
from app.schemas.pain_points import (
    AnnotationCreateRequest,
    MergeRequest,
    PainPointDetail,
    PainPointPatchRequest,
    RejectRequest,
    ReviewRequest,
)
from app.services.audit import write_audit
from app.services.scoring_service import recalculate_pain_point
from app.services.url_safety import validate_outbound_url


def _detail(session: Session, pain_point_id: uuid.UUID) -> PainPointDetail:
    pain_point = get_pain_point(session, pain_point_id, detail=True)
    if pain_point is None:
        raise AppError("RESOURCE_NOT_FOUND", "Pain point not found.", status_code=404)
    return PainPointDetail.model_validate(pain_point)


def get_pain_point_detail(session: Session, pain_point_id: uuid.UUID) -> PainPointDetail:
    return _detail(session, pain_point_id)


def get_pain_points(
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
    sort_by: str = "evidence_score",
    sort_order: str = "desc",
) -> tuple[list[PainPoint], int]:
    return list_pain_points(
        session,
        page=page,
        page_size=page_size,
        statuses=statuses,
        category_code=category_code,
        job_id=job_id,
        min_evidence_score=min_evidence_score,
        min_commercial_score=min_commercial_score,
        min_coverage_score=min_coverage_score,
        has_verified_evidence=has_verified_evidence,
        has_payment_signal=has_payment_signal,
        query=query,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def verify_pain_point(
    session: Session, pain_point_id: uuid.UUID, payload: ReviewRequest
) -> PainPointDetail:
    pain_point = get_pain_point(session, pain_point_id, detail=True)
    if pain_point is None:
        raise AppError("RESOURCE_NOT_FOUND", "Pain point not found.", status_code=404)
    if not pain_point.evidences:
        raise AppError(
            "EVIDENCE_URL_REQUIRED",
            "A pain point cannot be verified without persisted evidence.",
            status_code=422,
        )

    verifiable = [
        evidence
        for evidence in pain_point.evidences
        if evidence.quote_match_status
        in {QuoteMatchStatus.EXACT_MATCH, QuoteMatchStatus.NORMALIZED_MATCH}
    ]
    if not verifiable:
        raise AppError(
            "EVIDENCE_QUOTE_NOT_VERIFIED",
            "At least one quote must match accessible source text before verification.",
            status_code=422,
        )
    for evidence in verifiable:
        try:
            validate_outbound_url(evidence.source_url_snapshot, require_public_dns=False)
        except UrlSafetyError as exc:
            raise AppError(
                "EVIDENCE_URL_REQUIRED",
                "The evidence does not contain a legal HTTP(S) source URL.",
                status_code=422,
            ) from exc

    prior = pain_point.status.value
    pain_point.status = PainPointStatus.VERIFIED
    pain_point.last_reviewed_at = datetime.now(UTC)
    for evidence in verifiable:
        evidence.manual_verification_status = ManualVerificationStatus.VERIFIED
        evidence.manual_note = payload.reason
    write_audit(
        session,
        action="pain_point_verified",
        entity_type="pain_point",
        entity_id=pain_point.id,
        before_state={"status": prior},
        after_state={"status": pain_point.status.value},
        reason=payload.reason,
    )
    session.commit()
    return _detail(session, pain_point.id)


def reject_pain_point(
    session: Session, pain_point_id: uuid.UUID, payload: RejectRequest
) -> PainPointDetail:
    pain_point = get_pain_point(session, pain_point_id, detail=True)
    if pain_point is None:
        raise AppError("RESOURCE_NOT_FOUND", "Pain point not found.", status_code=404)
    prior = pain_point.status.value
    pain_point.status = PainPointStatus.REJECTED
    pain_point.last_reviewed_at = datetime.now(UTC)
    for evidence in pain_point.evidences:
        evidence.manual_verification_status = ManualVerificationStatus.REJECTED
        evidence.manual_note = payload.reason
    write_audit(
        session,
        action="pain_point_rejected",
        entity_type="pain_point",
        entity_id=pain_point.id,
        before_state={"status": prior},
        after_state={"status": pain_point.status.value},
        reason=payload.reason,
    )
    session.commit()
    return _detail(session, pain_point.id)


def patch_pain_point(
    session: Session, pain_point_id: uuid.UUID, payload: PainPointPatchRequest
) -> PainPointDetail:
    pain_point = get_pain_point(session, pain_point_id, detail=True)
    if pain_point is None:
        raise AppError("RESOURCE_NOT_FOUND", "Pain point not found.", status_code=404)
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    updates = payload.model_dump(exclude_unset=True)
    category_code = updates.pop("primary_category_code", None)
    if category_code is not None:
        category = session.scalar(
            select(TaxonomyCategory).where(TaxonomyCategory.code == category_code)
        )
        if category is None:
            raise AppError("VALIDATION_ERROR", "Unknown taxonomy category.", status_code=422)
        before["primary_category_code"] = pain_point.category.code if pain_point.category else None
        pain_point.primary_category_id = category.id
        after["primary_category_code"] = category.code
    for field_name, value in updates.items():
        if value is None:
            continue
        before[field_name] = getattr(pain_point, field_name)
        setattr(pain_point, field_name, value)
        after[field_name] = value
    write_audit(
        session,
        action="pain_point_updated",
        entity_type="pain_point",
        entity_id=pain_point.id,
        before_state=before,
        after_state=after,
    )
    session.commit()
    return _detail(session, pain_point.id)


def merge_pain_point(
    session: Session, pain_point_id: uuid.UUID, payload: MergeRequest
) -> PainPointDetail:
    if pain_point_id == payload.target_pain_point_id:
        raise AppError("CONFLICT", "A pain point cannot be merged into itself.", status_code=409)
    source = get_pain_point(session, pain_point_id, detail=True)
    target = get_pain_point(session, payload.target_pain_point_id, detail=True)
    if source is None or target is None:
        raise AppError("RESOURCE_NOT_FOUND", "Pain point not found.", status_code=404)
    if target.status in {PainPointStatus.DUPLICATE, PainPointStatus.REJECTED}:
        raise AppError("CONFLICT", "The merge target is not an active pain point.", status_code=409)

    target_keys = {
        (evidence.source_item_id, evidence.evidence_quote_normalized)
        for evidence in target.evidences
    }
    moved = 0
    for evidence in list(source.evidences):
        key = (evidence.source_item_id, evidence.evidence_quote_normalized)
        if key in target_keys:
            continue
        source.evidences.remove(evidence)
        evidence.pain_point_id = target.id
        target.evidences.append(evidence)
        target_keys.add(key)
        moved += 1
    source.status = PainPointStatus.DUPLICATE
    source.merged_into_id = target.id
    source.last_reviewed_at = datetime.now(UTC)
    recalculate_pain_point(session, target)
    write_audit(
        session,
        action="pain_point_merged",
        entity_type="pain_point",
        entity_id=source.id,
        before_state={"status": "active", "evidence_count": len(source.evidences) + moved},
        after_state={"status": source.status.value, "merged_into": str(target.id), "moved": moved},
        reason=payload.reason,
    )
    write_audit(
        session,
        action="pain_point_merge_target_updated",
        entity_type="pain_point",
        entity_id=target.id,
        before_state={},
        after_state={"evidence_count": len(target.evidences), "moved": moved},
        reason=payload.reason,
    )
    session.commit()
    return _detail(session, target.id)


def rescore_pain_point(session: Session, pain_point_id: uuid.UUID) -> PainPointDetail:
    pain_point = get_pain_point(session, pain_point_id, detail=True)
    if pain_point is None:
        raise AppError("RESOURCE_NOT_FOUND", "Pain point not found.", status_code=404)
    recalculate_pain_point(session, pain_point)
    write_audit(
        session,
        action="pain_point_rescored",
        entity_type="pain_point",
        entity_id=pain_point.id,
        after_state={
            "evidence_score": pain_point.evidence_confidence_score,
            "commercial_score": pain_point.commercial_opportunity_score,
        },
    )
    session.commit()
    return _detail(session, pain_point.id)


def add_annotation(
    session: Session, pain_point_id: uuid.UUID, payload: AnnotationCreateRequest
) -> Annotation:
    pain_point = get_pain_point(session, pain_point_id)
    if pain_point is None:
        raise AppError("RESOURCE_NOT_FOUND", "Pain point not found.", status_code=404)
    annotation = Annotation(
        pain_point_id=pain_point.id,
        annotation_type=payload.annotation_type,
        content=payload.content,
        actor="local-user",
    )
    session.add(annotation)
    write_audit(
        session,
        action="annotation_added",
        entity_type="pain_point",
        entity_id=pain_point.id,
        after_state={"annotation_type": payload.annotation_type},
    )
    session.commit()
    session.refresh(annotation)
    return annotation
