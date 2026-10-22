"""Provider policy, health, and credential-reference persistence."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProviderHealth(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    BLOCKED = "blocked"


def provider_health_type() -> Enum:
    return Enum(
        ProviderHealth,
        name="provider_health",
        native_enum=False,
        length=16,
        values_callable=lambda enum_type: [item.value for item in enum_type],
    )


class SourceProvider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_providers"

    provider_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    access_method: Mapped[str] = mapped_column(String(64), nullable=False, default="official_api")
    terms_url: Mapped[str | None] = mapped_column(String(2_048))
    policy_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_confirmed_by: Mapped[str | None] = mapped_column(String(160))
    rate_limit_config: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    capabilities: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    credentials_ref: Mapped[str | None] = mapped_column(String(160))
    health_status: Mapped[ProviderHealth] = mapped_column(
        provider_health_type(), nullable=False, default=ProviderHealth.UNKNOWN
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_summary: Mapped[str | None] = mapped_column(Text)
