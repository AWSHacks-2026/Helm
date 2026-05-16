#!/usr/bin/env python3
"""CLI: compare Overlord vs naive baselines for all merge scenarios."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

BASE = os.getenv("OVERLORD_API", "http://127.0.0.1:8000")


def main() -> int:
    os.environ.setdefault("OVERLORD_MOCK_BEDROCK", "1")
    client = httpx.Client(base_url=BASE, timeout=60.0)
    scenarios = client.get("/merge/scenarios").json()
    failed = 0
    for meta in scenarios:
        name = meta["name"]
        result = client.post(f"/merge/compare/{name}").json()
        summary = result["summary"]
        ok = summary["overlord_passed"] and summary["overlord_beats_naive"]
        status = "PASS" if ok else "FAIL"
        print(
            f"[{status}] {name}: overlord {summary['overlord_score']}% "
            f"vs naive {summary['best_naive_score']}% ({summary['best_naive_strategy']})"
        )
        if not ok:
            failed += 1
            print(json.dumps(summary, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
