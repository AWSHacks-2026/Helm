#!/usr/bin/env python3
"""ShopFix real git: baseline merge chain vs parallel fleet merge (speed + cost)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

env_path = ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        pass

for p in (BACKEND, ROOT):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from agents.shopfix_merge_fleet_benchmark import (  # noqa: E402
    format_shopfix_merge_summary,
    run_shopfix_merge_fleet_benchmark,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ShopFix merge fleet benchmark (real git + Bedrock)"
    )
    parser.add_argument("--suite", default="contention", choices=["contention", "intent_opposition"])
    parser.add_argument("--agents", type=int, default=6)
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Allow HELM_MOCK_BEDROCK=1",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if os.getenv("HELM_MOCK_BEDROCK", "0") == "1" and not args.allow_mock:
        print(
            "ERROR: HELM_MOCK_BEDROCK=1 — set HELM_MOCK_BEDROCK=0 for live metrics or --allow-mock",
            file=sys.stderr,
        )
        return 2

    with tempfile.TemporaryDirectory(prefix="shopfix-merge-fleet-") as tmp:
        result = run_shopfix_merge_fleet_benchmark(
            suite=args.suite,
            agent_count=args.agents,
            work_dir=Path(tmp),
        )

    print(format_shopfix_merge_summary(result), flush=True)

    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"shopfix_merge_fleet_{stamp}.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "merge_fleet_strategy": os.getenv("MERGE_FLEET_STRATEGY", "haiku_chain"),
        "merge_fleet_parallel": os.getenv("MERGE_FLEET_PARALLEL", "1"),
        **result,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    if args.json:
        print(json.dumps(payload, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
