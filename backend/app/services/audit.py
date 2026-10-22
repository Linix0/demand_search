"""Append-only audit helpers for review and control actions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.research import AuditLog


def write_audit(
    session: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    reason: str = "",
    actor: str = "local-user",
) -> None:
    session.add(
        AuditLog(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state or {},
            after_state=after_state or {},
            reason=reason,
        )
    )
