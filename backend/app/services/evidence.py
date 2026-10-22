"""Deterministic evidence quote matching with offset preservation."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.models.pain_point import QuoteMatchStatus

MIN_QUOTE_CHARS = 20
MAX_QUOTE_CHARS = 500

PAYMENT_SIGNAL_PATTERNS = tuple(
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"(?<![\w-])budget (?:has been )?approved(?![\w-])",
        r"(?<![\w-])approved budget(?![\w-])",
        r"(?<![\w-])we bought(?![\w-])",
        r"(?<![\w-])we paid(?![\w-])",
        r"(?<![\w-])purchase order(?![\w-])",
        r"(?<![\w-])paid for(?![\w-])",
        r"预算(?:已经|已)批准",
        r"已(?:经)?(?:购买|付款|付费)",
        r"(?:采购订单|付费替代)",
    )
)

PAYMENT_NEGATION_PATTERNS = tuple(
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"(?<![\w-])(?:no|not|never|without)(?: [\w-]+){0,2} "
        r"(?:budget|approved|bought|paid|purchase|order|premium|pay)(?![\w-])",
        r"(?:没有|没|未|尚未|还没有|并无|并非)(?: [\w-]+){0,2}"
        r"(?:预算|获批|批准|购买|付款|付费|采购|订单)",
    )
)


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


def detect_payment_signal(text: str) -> bool:
    """Detect a narrow, affirmative payment signal in a verified evidence quote."""

    normalized = re.sub(r"\s+", " ", normalize_evidence_text(text).casefold()).strip()
    if any(pattern.search(normalized) for pattern in PAYMENT_NEGATION_PATTERNS):
        return False
    return any(pattern.search(normalized) for pattern in PAYMENT_SIGNAL_PATTERNS)


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
