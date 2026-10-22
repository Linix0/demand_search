"""Deterministic LLM substitute for offline integration tests."""

from __future__ import annotations

import re

from app.providers.llm.base import ExtractionRequest, ExtractionResponse, LLMProvider


class MockLLMProvider(LLMProvider):
    code = "mock"

    def extract_candidates(self, request: ExtractionRequest) -> ExtractionResponse:
        if not 1 <= request.max_candidates <= 5:
            raise ValueError("Mock extraction supports 1-5 candidates")
        if not request.source_text.strip():
            return ExtractionResponse(source_item_id=request.source_item_id, candidates=[])

        source_text = request.source_text.strip()
        quote = source_text[:300]
        if len(quote) < 20:
            return ExtractionResponse(source_item_id=request.source_item_id, candidates=[])

        lowered = source_text.lower()
        payment_explicit = any(
            marker in lowered for marker in ("budget approved", "purchase", "already paid")
        )
        first_sentence = re.split(r"(?<=[.!?])\s+", source_text, maxsplit=1)[0][:180]
        if "small team" in lowered:
            user_segment = "small_business"
        elif "teams" in lowered:
            user_segment = "developer_team"
        else:
            user_segment = "unknown"

        if "spreadsheet" in lowered:
            workaround = "spreadsheet"
            tags = ["repetitive_manual_work", "workflow_fragmentation"]
        elif "three tools" in lowered:
            workaround = "multiple_tools"
            tags = ["workflow_fragmentation", "integration_gap"]
        else:
            workaround = "manual_copy_paste"
            tags = ["repetitive_manual_work", "slow_process"]
        if payment_explicit:
            tags.append("high_cost")

        candidates = [
            {
                "source_item_id": request.source_item_id,
                "pain_statement": (
                    f"{first_sentence.rstrip('.')} — the workflow needs a more reliable, "
                    "lower-effort alternative."
                ),
                "user_segment": user_segment,
                "context": "Offline mock fixture",
                "problem_detail": (
                    "The user repeats work across tools, risks missing records, and has no "
                    "single source of truth."
                ),
                "current_workaround": workaround,
                "payment_signal": "explicit" if payment_explicit else "none",
                "evidence_quote": quote,
                "evidence_start_offset": 0,
                "evidence_end_offset": len(quote),
                "candidate_type": "explicit_payment" if payment_explicit else "first_person_pain",
                "tags": tags,
                "uncertainties": ["Mock extraction is not evidence of a real market."],
            }
        ]
        return ExtractionResponse(source_item_id=request.source_item_id, candidates=candidates)
