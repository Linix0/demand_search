"""Safe report serialization for untrusted research text."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from typing import Any

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: Any) -> str:
    """Prevent spreadsheet formula execution while preserving display text."""

    if value is None:
        return ""
    text = str(value)
    stripped = text.lstrip()
    if text.startswith(FORMULA_PREFIXES) or stripped.startswith(FORMULA_PREFIXES):
        return f"'{text}"
    return text


def render_csv(rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> str:
    """Render UTF-8 CSV with every cell passed through the formula sanitizer."""

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: sanitize_csv_cell(row.get(field)) for field in fieldnames})
    return buffer.getvalue()
