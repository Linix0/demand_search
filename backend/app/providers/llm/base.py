"""Provider-neutral LLM boundary; outputs remain untrusted data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ExtractionRequest:
    source_item_id: str
    source_text: str
    max_candidates: int = 5


@dataclass(frozen=True, slots=True)
class ExtractionResponse:
    source_item_id: str
    candidates: list[dict[str, Any]]


class LLMProvider(Protocol):
    code: str

    def extract_candidates(self, request: ExtractionRequest) -> ExtractionResponse: ...
