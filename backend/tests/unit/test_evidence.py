"""Evidence quote verification tests."""

from __future__ import annotations

import pytest

from app.services.evidence import QuoteMatchStatus, verify_evidence_quote

QUOTE = "Every week I copy the same fields into a spreadsheet."


def test_exact_quote_match_preserves_offsets() -> None:
    source = f"Context before. {QUOTE} Context after."
    result = verify_evidence_quote(source, QUOTE)

    assert result.status == QuoteMatchStatus.EXACT_MATCH
    assert source[result.start_offset or 0 : result.end_offset or 0] == QUOTE


def test_normalized_match_handles_unicode_and_whitespace() -> None:
    source = "Every   week I copy the same fields into a spreadsheet."
    result = verify_evidence_quote(source, QUOTE)

    assert result.status == QuoteMatchStatus.NORMALIZED_MATCH
    assert result.is_verified is True
    assert result.start_offset == 0


def test_snippet_only_is_never_reported_as_full_text_match() -> None:
    result = verify_evidence_quote(None, QUOTE, content_completeness="snippet_only")

    assert result.status == QuoteMatchStatus.SNIPPET_ONLY
    assert result.is_verified is False


def test_missing_quote_is_not_found() -> None:
    result = verify_evidence_quote("A different source text without that sentence.", QUOTE)

    assert result.status == QuoteMatchStatus.NOT_FOUND
    assert result.is_verified is False


def test_too_short_quote_is_rejected() -> None:
    with pytest.raises(ValueError):
        verify_evidence_quote(QUOTE, "too short")
