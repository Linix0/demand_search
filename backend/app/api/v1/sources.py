"""Source pool browsing, manual URL import, and URL rechecks."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db_session
from app.core.config import Settings
from app.models.source import ContentCompleteness
from app.repositories.sources import get_source
from app.schemas.sources import (
    ManualUrlImportRequest,
    SourceListResponse,
    SourceRead,
    UrlRecheckResponse,
)
from app.services.sources import get_sources, import_manual_url, recheck_source

router = APIRouter(prefix="/api/v1/source-items", tags=["source-items"])
SessionDep = Annotated[Session, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


@router.get("", response_model=SourceListResponse)
def list_source_items(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    job_id: uuid.UUID | None = None,
    provider_code: str | None = None,
    source_domain: str | None = None,
    completeness: ContentCompleteness | None = None,
    q: str | None = None,
) -> SourceListResponse:
    items, total = get_sources(
        session,
        page=page,
        page_size=page_size,
        job_id=job_id,
        provider_code=provider_code,
        source_domain=source_domain,
        completeness=completeness,
        query=q,
    )
    return SourceListResponse(
        items=[SourceRead.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{source_id}", response_model=SourceRead)
def get_source_item(source_id: uuid.UUID, session: SessionDep) -> SourceRead:
    source = get_source(session, source_id)
    if source is None:
        from app.core.errors import AppError

        raise AppError("RESOURCE_NOT_FOUND", "Source item not found.", status_code=404)
    return SourceRead.model_validate(source)


@router.post("/import-url", response_model=UrlRecheckResponse, status_code=status.HTTP_201_CREATED)
def import_url(
    payload: ManualUrlImportRequest,
    session: SessionDep,
    settings: SettingsDep,
) -> UrlRecheckResponse:
    source, message = import_manual_url(
        session, raw_url=payload.url, title=payload.title, settings=settings
    )
    return UrlRecheckResponse(source=SourceRead.model_validate(source), message=message)


@router.post("/{source_id}/recheck-url", response_model=UrlRecheckResponse)
def recheck_url(
    source_id: uuid.UUID, session: SessionDep, settings: SettingsDep
) -> UrlRecheckResponse:
    source, message = recheck_source(session, source_id, settings)
    return UrlRecheckResponse(source=SourceRead.model_validate(source), message=message)


@router.post("/{source_id}/mark-irrelevant", response_model=UrlRecheckResponse)
def mark_source_irrelevant(source_id: uuid.UUID, session: SessionDep) -> UrlRecheckResponse:
    from app.core.errors import AppError

    source = get_source(session, source_id)
    if source is None:
        raise AppError("RESOURCE_NOT_FOUND", "Source item not found.", status_code=404)
    source.relevance_score = 0
    source.raw_metadata = {**source.raw_metadata, "marked_irrelevant": True}
    session.commit()
    session.refresh(source)
    return UrlRecheckResponse(
        source=SourceRead.model_validate(source), message="Source marked irrelevant."
    )
