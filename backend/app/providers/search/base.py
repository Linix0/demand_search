"""Provider-neutral search contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    keyword_search: bool = False
    date_filter: bool = False
    pagination: bool = False
    full_content: bool = False
    author_identity: bool = False
    engagement_metrics: bool = False
    permalink: bool = False
    rate_limit_info: bool = False
    commercial_use: bool = False


@dataclass(frozen=True, slots=True)
class SearchRequest:
    query: str
    language: str = "zh-CN"
    limit: int = 30
    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    provider_code: str
    external_id: str
    title: str
    url: str
    snippet: str
    published_at: datetime | None = None
    author: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SearchProvider(Protocol):
    code: str
    display_name: str
    capabilities: ProviderCapabilities

    def search(self, request: SearchRequest) -> list[SearchResult]: ...
