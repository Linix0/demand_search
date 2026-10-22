"""Describe configured providers without ever exposing credentials."""

from __future__ import annotations

from app.core.config import Settings
from app.schemas.provider import ProviderCapability, ProviderStatus


def list_provider_statuses(settings: Settings) -> list[ProviderStatus]:
    """Return Phase 0 provider capabilities and configuration state."""

    return [
        ProviderStatus(
            provider_code="mock",
            display_name="Mock Search",
            category="search",
            enabled=True,
            configured=True,
            health_status="healthy",
            access_method="local_fixture",
            capabilities=ProviderCapability(
                keyword_search=True,
                date_filter=True,
                full_content=False,
                permalink=True,
                commercial_use=True,
            ),
            note="Offline deterministic provider used for the full demo path.",
        ),
        ProviderStatus(
            provider_code="manual_url",
            display_name="Manual URL Import",
            category="source",
            enabled=True,
            configured=True,
            health_status="healthy",
            access_method="allowed_public_fetch",
            capabilities=ProviderCapability(full_content=True, permalink=True, commercial_use=True),
            note=(
                "Manual HTTP(S) import is enabled behind SSRF validation, redirect checks, "
                "content-type limits, and response-size limits."
            ),
        ),
        ProviderStatus(
            provider_code="github",
            display_name="GitHub Issues / Discussions",
            category="source",
            enabled=False,
            configured=bool(settings.github_token),
            health_status="disabled",
            access_method="official_api",
            policy_url="https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api",
            capabilities=ProviderCapability(
                keyword_search=True,
                date_filter=True,
                full_content=True,
                permalink=True,
                commercial_use=True,
            ),
            note="Disabled until Phase 2 provider onboarding and policy confirmation.",
        ),
        ProviderStatus(
            provider_code="search_tavily",
            display_name="Tavily Search",
            category="search",
            enabled=False,
            configured=bool(settings.tavily_api_key),
            health_status="disabled",
            access_method="search_api",
            policy_url="https://tavily.com/",
            capabilities=ProviderCapability(keyword_search=True, date_filter=False, permalink=True),
            note="Optional search adapter; disabled until Phase 2.",
        ),
        ProviderStatus(
            provider_code="search_brave",
            display_name="Brave Search API",
            category="search",
            enabled=False,
            configured=bool(settings.brave_search_api_key),
            health_status="disabled",
            access_method="search_api",
            policy_url="https://brave.com/search/api/",
            capabilities=ProviderCapability(keyword_search=True, date_filter=True, permalink=True),
            note="Optional search adapter; disabled until Phase 2.",
        ),
        ProviderStatus(
            provider_code="reddit",
            display_name="Reddit",
            category="source",
            enabled=False,
            configured=bool(settings.reddit_client_id and settings.reddit_client_secret),
            health_status="disabled",
            access_method="official_api",
            policy_url="https://redditinc.com/policies/data-api-terms",
            capabilities=ProviderCapability(
                keyword_search=True, date_filter=True, full_content=True, permalink=True
            ),
            note="Opt-in only after authorized credentials and current-terms confirmation.",
        ),
        ProviderStatus(
            provider_code="llm_mock",
            display_name="Mock LLM",
            category="llm",
            enabled=True,
            configured=True,
            health_status="healthy",
            access_method="local_fixture",
            capabilities=ProviderCapability(commercial_use=True),
            note=(
                "Deterministic extraction substitute; output still requires schema and "
                "evidence validation."
            ),
        ),
        ProviderStatus(
            provider_code="embedding_mock",
            display_name="Mock Embedding",
            category="embedding",
            enabled=True,
            configured=True,
            health_status="healthy",
            access_method="local_fixture",
            capabilities=ProviderCapability(commercial_use=True),
            note="Optional similarity helper; the pipeline also supports rule-only fallback.",
        ),
    ]
