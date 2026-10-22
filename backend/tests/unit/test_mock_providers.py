"""Offline provider determinism and limit tests."""

from __future__ import annotations

import pytest

from app.providers.llm.base import ExtractionRequest
from app.providers.llm.mock import MockLLMProvider
from app.providers.search.base import SearchRequest
from app.providers.search.mock import MockSearchProvider


def test_mock_search_is_deterministic_and_respects_limit() -> None:
    provider = MockSearchProvider()
    first = provider.search(SearchRequest(query="invoice reconciliation", limit=2))
    second = provider.search(SearchRequest(query="invoice reconciliation", limit=2))

    assert first == second
    assert len(first) == 2
    assert all(result.provider_code == "mock" for result in first)


def test_mock_search_rejects_empty_query() -> None:
    with pytest.raises(ValueError):
        MockSearchProvider().search(SearchRequest(query="  "))


def test_mock_llm_binds_source_id_and_quote() -> None:
    response = MockLLMProvider().extract_candidates(
        ExtractionRequest(
            source_item_id="source-1",
            source_text="Every week I copy fields into a spreadsheet and still miss records.",
        )
    )

    assert response.source_item_id == "source-1"
    assert response.candidates[0]["source_item_id"] == "source-1"
    assert response.candidates[0]["evidence_quote"].startswith("Every week")
