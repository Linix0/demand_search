"""Pain-point workbench API with server-side filtering and review actions."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models.pain_point import PainPointStatus
from app.schemas.pain_points import (
    AnnotationCreateRequest,
    AnnotationRead,
    MergeRequest,
    PainPointDetail,
    PainPointListItem,
    PainPointListResponse,
    PainPointPatchRequest,
    RejectRequest,
    ReviewActionResponse,
    ReviewRequest,
)
from app.services.pain_points import (
    add_annotation,
    get_pain_point_detail,
    get_pain_points,
    merge_pain_point,
    patch_pain_point,
    reject_pain_point,
    rescore_pain_point,
    verify_pain_point,
)

router = APIRouter(prefix="/api/v1/pain-points", tags=["pain-points"])
SessionDep = Annotated[Session, Depends(get_db_session)]


def _statuses(raw: str | None) -> list[PainPointStatus] | None:
    if not raw:
        return None
    values = [value.strip() for value in raw.split(",") if value.strip()]
    try:
        return [PainPointStatus(value) for value in values]
    except ValueError:
        from app.core.errors import AppError

        raise AppError("VALIDATION_ERROR", "Unknown pain-point status.", status_code=422) from None


@router.get("", response_model=PainPointListResponse)
def list_pain_points(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    statuses: str | None = None,
    category: str | None = None,
    job_id: uuid.UUID | None = None,
    min_evidence_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    min_commercial_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    min_coverage_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    has_verified_evidence: bool | None = None,
    has_payment_signal: bool | None = None,
    q: str | None = None,
    sort_by: Annotated[
        str,
        Query(
            pattern="^(created_at|updated_at|evidence_score|commercial_score|coverage_score|last_evidence_at)$"
        ),
    ] = "evidence_score",
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> PainPointListResponse:
    items, total = get_pain_points(
        session,
        page=page,
        page_size=page_size,
        statuses=_statuses(statuses),
        category_code=category,
        job_id=job_id,
        min_evidence_score=min_evidence_score,
        min_commercial_score=min_commercial_score,
        min_coverage_score=min_coverage_score,
        has_verified_evidence=has_verified_evidence,
        has_payment_signal=has_payment_signal,
        query=q,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    warning = None
    if items and max(item.coverage_score for item in items) < 50:
        warning = "Sample coverage is low; do not over-interpret these scores."
    return PainPointListResponse(
        items=[PainPointListItem.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        coverage_warning=warning,
    )


@router.get("/{pain_point_id}", response_model=PainPointDetail)
def get_pain_point(pain_point_id: uuid.UUID, session: SessionDep) -> PainPointDetail:
    return get_pain_point_detail(session, pain_point_id)


@router.patch("/{pain_point_id}", response_model=PainPointDetail)
def update_pain_point(
    pain_point_id: uuid.UUID, payload: PainPointPatchRequest, session: SessionDep
) -> PainPointDetail:
    return patch_pain_point(session, pain_point_id, payload)


@router.post("/{pain_point_id}/verify", response_model=ReviewActionResponse)
def verify(
    pain_point_id: uuid.UUID, payload: ReviewRequest, session: SessionDep
) -> ReviewActionResponse:
    detail = verify_pain_point(session, pain_point_id, payload)
    return ReviewActionResponse(pain_point=detail, message="Pain point verified by human review.")


@router.post("/{pain_point_id}/reject", response_model=ReviewActionResponse)
def reject(
    pain_point_id: uuid.UUID, payload: RejectRequest, session: SessionDep
) -> ReviewActionResponse:
    detail = reject_pain_point(session, pain_point_id, payload)
    return ReviewActionResponse(pain_point=detail, message="Pain point rejected.")


@router.post("/{pain_point_id}/merge", response_model=ReviewActionResponse)
def merge(
    pain_point_id: uuid.UUID, payload: MergeRequest, session: SessionDep
) -> ReviewActionResponse:
    detail = merge_pain_point(session, pain_point_id, payload)
    return ReviewActionResponse(
        pain_point=detail, message="Pain point merged with evidence preserved."
    )


@router.post("/{pain_point_id}/rescore", response_model=ReviewActionResponse)
def rescore(pain_point_id: uuid.UUID, session: SessionDep) -> ReviewActionResponse:
    detail = rescore_pain_point(session, pain_point_id)
    return ReviewActionResponse(
        pain_point=detail, message="Scores recalculated from persisted evidence."
    )


@router.post("/{pain_point_id}/annotations", response_model=AnnotationRead, status_code=201)
def create_annotation(
    pain_point_id: uuid.UUID, payload: AnnotationCreateRequest, session: SessionDep
) -> AnnotationRead:
    return AnnotationRead.model_validate(add_annotation(session, pain_point_id, payload))
