"""Evidence-preserving export downloads."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models.pain_point import PainPointStatus
from app.schemas.export import ExportRequest
from app.services.exports import build_export

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])
SessionDep = Annotated[Session, Depends(get_db_session)]


@router.post("/pain-points")
def export_pain_points(payload: ExportRequest, session: SessionDep) -> Response:
    job_id = uuid.UUID(payload.job_id) if payload.job_id else None
    export_status = PainPointStatus(payload.status) if payload.status else None
    result = build_export(
        session,
        export_format=payload.format,
        job_id=job_id,
        status=export_status,
        max_items=payload.max_items,
    )
    return Response(
        content=result.content.encode("utf-8"),
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Export-Rows": str(result.row_count),
            "Cache-Control": "no-store",
        },
    )
