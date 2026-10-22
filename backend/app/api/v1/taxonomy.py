"""Database-backed category and tag endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.taxonomy import (
    CategoryListResponse,
    CategoryResponse,
    TagListResponse,
    TagResponse,
)
from app.services.taxonomy import list_categories, list_tags
from app.services.workspace import ensure_default_workspace

router = APIRouter(prefix="/api/v1/taxonomy", tags=["taxonomy"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.get("/categories", response_model=CategoryListResponse)
def categories(session: SessionDep) -> CategoryListResponse:
    ensure_default_workspace(session)
    session.commit()
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(item) for item in list_categories(session)]
    )


@router.get("/tags", response_model=TagListResponse)
def tags(session: SessionDep) -> TagListResponse:
    ensure_default_workspace(session)
    session.commit()
    return TagListResponse(items=[TagResponse.model_validate(item) for item in list_tags(session)])
