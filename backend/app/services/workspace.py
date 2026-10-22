"""Single-user workspace bootstrap with explicit future tenancy boundary."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.services.taxonomy import ensure_taxonomy


def ensure_default_workspace(session: Session) -> Workspace:
    workspace = session.scalar(select(Workspace).order_by(Workspace.created_at).limit(1))
    if workspace is None:
        workspace = Workspace(name="Local research workspace", timezone="Asia/Shanghai")
        session.add(workspace)
        session.flush()
    ensure_taxonomy(session)
    session.flush()
    return workspace
