#!/usr/bin/env python3
"""Stable entry point for the site generator. Exits 0 on a clean build."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.generator import build  # noqa: E402


def main() -> int:
    path, size, kept, dropped = build()
    print(f"wrote {path} ({size:,} bytes, {kept} listed, {dropped} excluded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
