"""Evidence quote verification and payment-rule tests."""

from __future__ import annotations

import pytest

from app.services.evidence import (
    QuoteMatchStatus,
    detect_payment_signal,
    verify_evidence_quote,
)

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


@pytest.mark.parametrize(
    "quote",
    [
        "Our small team has a budget approved for a better tool.",
        "The manager signed the purchase order last Friday.",
        "We paid for a paid alternative and it still does not fit our workflow.",
        "客户的预算已批准,但团队仍然依赖手工表格完成汇总。",
    ],
)
def test_detect_payment_signal_accepts_explicit_affirmative_quotes(quote: str) -> None:
    assert detect_payment_signal(quote) is True


@pytest.mark.parametrize(
    "quote",
    [
        "Every week I copy the same fields into a spreadsheet.",
        "We have no approved budget for a better tool right now.",
        "The team has not paid for any substitute and still works manually.",
        "我们尚未获得预算批准,目前仍然使用手工表格。",
        "I would pay anything to make this boring task disappear.",
    ],
)
def test_detect_payment_signal_rejects_ambiguous_or_negated_quotes(quote: str) -> None:
    assert detect_payment_signal(quote) is False


def test_detect_payment_signal_normalizes_case_width_and_whitespace() -> None:
    assert detect_payment_signal("  WE\tPURCHASED... wait, BUDGET   APPROVED!  ") is True
