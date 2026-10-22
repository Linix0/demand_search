"""Deterministic offline search provider for demos and integration tests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from app.providers.search.base import (
    ProviderCapabilities,
    SearchProvider,
    SearchRequest,
    SearchResult,
)


class MockSearchProvider(SearchProvider):
    code = "mock"
    display_name = "Mock Search"
    capabilities = ProviderCapabilities(
        keyword_search=True,
        date_filter=True,
        pagination=False,
        full_content=False,
        author_identity=False,
        engagement_metrics=False,
        permalink=True,
        rate_limit_info=True,
        commercial_use=True,
    )

    def search(self, request: SearchRequest) -> list[SearchResult]:
        if not request.query.strip():
            raise ValueError("Search query must not be empty")
        if not 1 <= request.limit <= 100:
            raise ValueError("Search limit must be within 1-100")

        query_digest = hashlib.sha256(request.query.encode("utf-8")).hexdigest()[:10]
        base_url = f"https://example.com/mock/{query_digest}"
        fixtures = [
            SearchResult(
                provider_code=self.code,
                external_id=f"mock-{query_digest}-issue",
                title=f"{request.query}: recurring manual export workflow",
                url=f"{base_url}/issues/101",
                snippet=(
                    "Every week I copy the same fields into a spreadsheet and still miss records."
                ),
                published_at=datetime(2026, 9, 20, 8, 0, tzinfo=UTC),
                metadata={
                    "fixture": True,
                    "content_completeness": "full_public_content",
                    "trust_tier": "A_primary_user_report",
                    "author": "fixture-author-alpha",
                },
            ),
            SearchResult(
                provider_code=self.code,
                external_id=f"mock-{query_digest}-forum",
                title=f"Looking for a better way to handle {request.query}",
                url=f"{base_url}/forum/threads/202",
                snippet=(
                    "Our small team has a budget approved for a better tool, but the current "
                    "process is still completely manual."
                ),
                published_at=datetime(2026, 10, 2, 10, 30, tzinfo=UTC),
                metadata={
                    "fixture": True,
                    "content_completeness": "snippet_only",
                    "trust_tier": "D_search_snippet",
                    "author": "fixture-author-beta",
                },
            ),
            SearchResult(
                provider_code=self.code,
                external_id=f"mock-{query_digest}-review",
                title=f"Review: {request.query} tools are fragmented",
                url=f"{base_url}/reviews/303",
                snippet="Teams switch between three tools and still reconcile the data by hand.",
                published_at=datetime(2026, 8, 11, 2, 0, tzinfo=UTC),
                metadata={
                    "fixture": True,
                    "content_completeness": "partial_content",
                    "trust_tier": "C_secondary_review",
                    "author": "fixture-author-gamma",
                },
            ),
        ]
        return fixtures[: request.limit]
