"""Manual URL import and source pool read operations."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import structlog
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, UrlSafetyError
from app.models.source import (
    ContentCompleteness,
    RetrievalMethod,
    SourceItem,
    SourceTrustTier,
    UrlStatus,
)
from app.repositories.sources import (
    find_source_by_canonical_url,
    get_source,
    list_sources,
)
from app.services.evidence import normalize_evidence_text
from app.services.fetcher import (
    ResponseTooLargeError,
    SafeFetcher,
    UnsafeContentTypeError,
    describe_fetch_error,
)
from app.services.url_safety import validate_outbound_url

logger = structlog.get_logger(__name__)

SSRF_CODES = {
    "INVALID_SCHEME",
    "HOST_REQUIRED",
    "URL_CREDENTIALS_NOT_ALLOWED",
    "INVALID_PORT",
    "PORT_NOT_ALLOWED",
    "HOST_NOT_ALLOWED",
    "DNS_RESOLUTION_FAILED",
    "INVALID_RESOLVED_ADDRESS",
    "NON_PUBLIC_ADDRESS",
    "INVALID_URL",
    "URL_TOO_LONG",
    "URL_REQUIRED",
    "INVALID_REDIRECT",
    "TOO_MANY_REDIRECTS",
    "PEER_ADDRESS_UNAVAILABLE",
}


def _source_name(domain: str) -> str:
    if domain.endswith("github.com"):
        return "GitHub"
    if domain.endswith("news.ycombinator.com"):
        return "Hacker News"
    if domain.endswith("reddit.com"):
        return "Reddit"
    return domain


def _trust_tier(domain: str) -> SourceTrustTier:
    if domain.endswith(("github.com", "stackoverflow.com", "news.ycombinator.com")):
        return SourceTrustTier.A_PRIMARY_USER_REPORT
    return SourceTrustTier.C_SECONDARY_REVIEW


def import_manual_url(
    session: Session,
    *,
    raw_url: str,
    title: str,
    settings: Settings,
) -> tuple[SourceItem, str]:
    try:
        canonical_url = validate_outbound_url(
            raw_url,
            allowed_ports=settings.allowed_ports,
            require_public_dns=True,
        )
    except UrlSafetyError as exc:
        raise AppError(
            "SSRF_BLOCKED",
            "The URL violates the outbound source safety policy.",
            status_code=400,
            details={"reason": exc.code},
        ) from exc

    existing = find_source_by_canonical_url(session, canonical_url)
    if existing is not None:
        return existing, "This source already exists in the source pool."

    domain = (urlsplit(canonical_url).hostname or "").lower()
    page = None
    fetch_error_code: str | None = None
    fetch_error_message: str | None = None
    try:
        page = SafeFetcher(settings).fetch(canonical_url)
    except (UrlSafetyError, UnsafeContentTypeError, ResponseTooLargeError) as exc:
        code, message = describe_fetch_error(exc)
        if code in SSRF_CODES:
            raise AppError(
                "SSRF_BLOCKED",
                "The URL violates the outbound source safety policy.",
                status_code=400,
                details={"reason": code},
            ) from exc
        fetch_error_code, fetch_error_message = code, message
    except Exception as exc:
        fetch_error_code = "SOURCE_FETCH_FAILED"
        fetch_error_message = "The source could not be retrieved."
        logger.warning(
            "manual_source_import_failed",
            domain=domain,
            error_type=type(exc).__name__,
        )

    now = datetime.now(UTC)
    if page is not None:
        text = page.text
        title_value = (title.strip() or page.title or domain)[:300]
        completeness, content_text = _content_retention(text, settings)
        content_excerpt = text[:500]
        url_status = (
            UrlStatus.REDIRECTED if page.final_url != page.requested_url else UrlStatus.REACHABLE
        )
        message = (
            "Public source imported with full text retained because the operator enabled it."
            if content_text is not None
            else "Public source imported and retained with a bounded excerpt."
        )
    else:
        title_value = (title.strip() or domain)[:300]
        completeness = ContentCompleteness.METADATA_ONLY
        content_text = None
        content_excerpt = None
        url_status = {
            "SOURCE_NOT_FOUND": UrlStatus.NOT_FOUND,
            "SOURCE_TIMEOUT": UrlStatus.TIMEOUT,
            "SOURCE_ACCESS_BLOCKED": UrlStatus.BLOCKED,
        }.get(fetch_error_code or "", UrlStatus.UNKNOWN_ERROR)
        message = fetch_error_message or "Source metadata saved, but content retrieval failed."

    content_hash_source = (page.text if page is not None else None) or canonical_url
    source = SourceItem(
        research_job_id=None,
        provider_code="manual_url",
        external_id=None,
        source_name=_source_name(domain),
        source_domain=domain,
        source_url=raw_url.strip(),
        canonical_url=canonical_url,
        final_url=page.final_url if page else None,
        source_title=title_value,
        published_at=None,
        collected_at=now,
        content_text=content_text,
        content_excerpt=content_excerpt,
        content_hash=hashlib.sha256(
            normalize_evidence_text(content_hash_source).encode("utf-8")
        ).hexdigest(),
        content_completeness=completeness,
        url_status=url_status,
        retrieval_method=RetrievalMethod.MANUAL_IMPORT,
        raw_metadata={"imported_by": "local-user", "fetch_error": fetch_error_code},
        relevance_score=60 if page else 20,
        source_trust_tier=_trust_tier(domain),
        is_duplicate=False,
        retention_until=now + timedelta(days=settings.default_retention_days),
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return source, message


def recheck_source(
    session: Session, source_id: uuid.UUID, settings: Settings
) -> tuple[SourceItem, str]:
    source = get_source(session, source_id)
    if source is None:
        raise AppError("RESOURCE_NOT_FOUND", "Source item not found.", status_code=404)
    page = SafeFetcher(settings).fetch(source.canonical_url)
    source.final_url = page.final_url
    source.url_status = (
        UrlStatus.REDIRECTED if page.final_url != page.requested_url else UrlStatus.REACHABLE
    )
    source.source_title = page.title or source.source_title
    source.content_completeness, source.content_text = _content_retention(page.text, settings)
    source.content_excerpt = page.text[:500]
    source.content_hash = hashlib.sha256(
        normalize_evidence_text(page.text).encode("utf-8")
    ).hexdigest()
    session.commit()
    session.refresh(source)
    return source, "Source URL rechecked and content refreshed."


def _content_retention(text: str, settings: Settings) -> tuple[ContentCompleteness, str | None]:
    if settings.store_full_page_text:
        completeness = (
            ContentCompleteness.FULL_PUBLIC_CONTENT
            if len(text) < 20_000
            else ContentCompleteness.PARTIAL_CONTENT
        )
        return completeness, text
    return ContentCompleteness.PARTIAL_CONTENT, None


def get_sources(
    session: Session,
    *,
    page: int,
    page_size: int,
    job_id: uuid.UUID | None = None,
    provider_code: str | None = None,
    source_domain: str | None = None,
    completeness: ContentCompleteness | None = None,
    query: str | None = None,
) -> tuple[list[SourceItem], int]:
    return list_sources(
        session,
        page=page,
        page_size=page_size,
        job_id=job_id,
        provider_code=provider_code,
        source_domain=source_domain,
        completeness=completeness,
        query=query,
    )
