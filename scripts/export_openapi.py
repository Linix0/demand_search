"""Write a deterministic OpenAPI snapshot used to regenerate frontend types."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
OUTPUT_PATH = REPO_ROOT / "frontend" / "openapi.json"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402


def render_schema() -> str:
    schema = app.openapi()
    return json.dumps(schema, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the committed snapshot differs from the application schema.",
    )
    args = parser.parse_args()

    rendered = render_schema()
    if args.check:
        if not OUTPUT_PATH.is_file():
            print(f"Missing OpenAPI snapshot: {OUTPUT_PATH}", file=sys.stderr)
            return 1
        if OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
            print(f"Outdated OpenAPI snapshot: {OUTPUT_PATH}", file=sys.stderr)
            return 1
        print(f"OpenAPI snapshot is current: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    path_count = len(app.openapi().get("paths", {}))
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} with {path_count} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
