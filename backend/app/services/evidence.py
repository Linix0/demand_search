"""Deterministic evidence quote matching with offset preservation."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from app.models.pain_point import QuoteMatchStatus

MIN_QUOTE_CHARS = 20
MAX_QUOTE_CHARS = 500


@dataclass(frozen=True, slots=True)
class QuoteVerification:
    status: QuoteMatchStatus
    normalized_quote: str
    start_offset: int | None = None
    end_offset: int | None = None

    @property
    def is_verified(self) -> bool:
        return self.status in {QuoteMatchStatus.EXACT_MATCH, QuoteMatchStatus.NORMALIZED_MATCH}


def _normalize_with_offsets(text: str) -> tuple[str, list[int]]:
    """Normalize Unicode and whitespace while retaining original character offsets."""

    normalized: list[str] = []
    offsets: list[int] = []
    previous_was_space = False

    for index, character in enumerate(text):
        if character.isspace():
            if not previous_was_space:
                normalized.append(" ")
                offsets.append(index)
            previous_was_space = True
            continue

        previous_was_space = False
        for expanded in unicodedata.normalize("NFKC", character):
            normalized.append(expanded)
            offsets.append(index)

    return "".join(normalized), offsets


def normalize_evidence_text(text: str) -> str:
    return _normalize_with_offsets(text)[0]


def verify_evidence_quote(
    source_text: str | None,
    quote: str,
    *,
    content_completeness: str = "full_public_content",
) -> QuoteVerification:
    """Match a short quote against source text without trusting model edits."""

    compact_quote = " ".join(quote.split())
    if not MIN_QUOTE_CHARS <= len(compact_quote) <= MAX_QUOTE_CHARS:
        raise ValueError(
            f"Evidence quote must contain {MIN_QUOTE_CHARS}-{MAX_QUOTE_CHARS} characters"
        )

    if content_completeness == "snippet_only":
        return QuoteVerification(
            status=QuoteMatchStatus.SNIPPET_ONLY,
            normalized_quote=normalize_evidence_text(compact_quote),
        )
    if not source_text:
        return QuoteVerification(
            status=QuoteMatchStatus.NOT_FOUND,
            normalized_quote=normalize_evidence_text(compact_quote),
        )

    exact_start = source_text.find(compact_quote)
    if exact_start >= 0:
        return QuoteVerification(
            status=QuoteMatchStatus.EXACT_MATCH,
            normalized_quote=normalize_evidence_text(compact_quote),
            start_offset=exact_start,
            end_offset=exact_start + len(compact_quote),
        )

    normalized_source, offset_map = _normalize_with_offsets(source_text)
    normalized_quote = normalize_evidence_text(compact_quote)
    normalized_start = normalized_source.find(normalized_quote)
    if normalized_start < 0:
        return QuoteVerification(
            status=QuoteMatchStatus.NOT_FOUND,
            normalized_quote=normalized_quote,
        )

    normalized_end = normalized_start + len(normalized_quote) - 1
    return QuoteVerification(
        status=QuoteMatchStatus.NORMALIZED_MATCH,
        normalized_quote=normalized_quote,
        start_offset=offset_map[normalized_start],
        end_offset=offset_map[normalized_end] + 1,
    )
