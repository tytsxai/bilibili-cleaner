"""Dump the FastAPI app's OpenAPI schema to stdout (or a path) as JSON.

Usage::

    python scripts/dump_openapi.py            # writes to openapi.json in repo root
    python scripts/dump_openapi.py -          # writes to stdout
    python scripts/dump_openapi.py path.json  # writes to path.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    from backend.main import app

    schema = app.openapi()
    payload = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)

    target = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    if target == "-":
        sys.stdout.write(payload + "\n")
        return
    Path(target).write_text(payload + "\n", encoding="utf-8")
    sys.stderr.write(f"wrote {target}\n")


if __name__ == "__main__":
    main()
