"""Non-secret provider configuration and health contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProviderCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keyword_search: bool = False
    date_filter: bool = False
    full_content: bool = False
    permalink: bool = False
    commercial_use: bool = False


class ProviderStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_code: str
    display_name: str
    category: Literal["search", "source", "llm", "embedding"]
    enabled: bool
    configured: bool
    health_status: Literal["unknown", "healthy", "degraded", "disabled", "blocked"]
    access_method: str
    policy_url: str | None = None
    capabilities: ProviderCapability = Field(default_factory=ProviderCapability)
    note: str


class ProviderListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ProviderStatus]


class ProviderTestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_code: str
    status: Literal["healthy"]
    message: str
