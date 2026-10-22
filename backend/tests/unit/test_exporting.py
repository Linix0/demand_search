"""CSV injection and serialization tests."""

from __future__ import annotations

import csv
import io

import pytest

from app.services.exporting import render_csv, sanitize_csv_cell


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_formula_prefixes_are_neutralized(prefix: str) -> None:
    assert sanitize_csv_cell(f"{prefix}cmd") == f"'{prefix}cmd"


def test_leading_whitespace_does_not_bypass_sanitizer() -> None:
    assert sanitize_csv_cell("  =SUM(A1:A2)") == "'  =SUM(A1:A2)"


def test_plain_text_and_none_are_preserved() -> None:
    assert sanitize_csv_cell("normal text") == "normal text"
    assert sanitize_csv_cell(None) == ""


def test_render_csv_sanitizes_every_row() -> None:
    output = render_csv(
        [{"statement": '=HYPERLINK("https://example.com")', "score": 80}],
        ["statement", "score"],
    )

    rows = list(csv.DictReader(io.StringIO(output)))
    assert rows[0]["statement"].startswith("'=")
    assert rows[0]["score"] == "80"
