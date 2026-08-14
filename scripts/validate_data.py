#!/usr/bin/env python3
"""Validate every harvested record, rendered or not. Exits 0 when clean.

This is the gate that makes "nothing was silently deleted" checkable rather
than promised: a record that is neither fully hand-annotated nor carrying a
written exclusion reason fails here, before the generator ever runs.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_model import DataValidationError, excluded, listed, validate_roster  # noqa: E402
from src.site_config import COUNTIES  # noqa: E402

ROSTER = ROOT / "data" / "roster.json"


def main() -> int:
    try:
        payload = json.loads(ROSTER.read_text(encoding="utf-8"))
        records = validate_roster(payload)
    except (json.JSONDecodeError, DataValidationError) as error:
        print(f"data validation failed: {error}", file=sys.stderr)
        return 1

    rows = listed(records)
    dropped = excluded(records)
    counties = Counter(r["county"] for r in rows)
    gaps = sum(1 for r in rows if r["web_gap_hand"])

    print(f"data validation passed: schema v1, {len(records)} harvested records")
    print(f"  listed   {len(rows)}")
    print(f"  excluded {len(dropped)} (each with a written reason)")
    print(f"  counties {', '.join(f'{c} {counties[c]}' for c in COUNTIES)}")
    print(f"  no web address of their own: {gaps}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
