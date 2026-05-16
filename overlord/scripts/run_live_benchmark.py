#!/usr/bin/env python3
"""Run live merge benchmark from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from agents.live_harness import run_benchmark  # noqa: E402
from agents.merge_scenarios import get_merge_scenario_names  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Live merge benchmark")
    parser.add_argument(
        "--scenario",
        default="merge_conflict",
        choices=get_merge_scenario_names(),
    )
    parser.add_argument(
        "--seed-mode",
        choices=["scenario", "haiku"],
        default="scenario",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON")
    args = parser.parse_args()

    result = run_benchmark(args.scenario, seed_mode=args.seed_mode)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        c = result["comparison"]
        print(
            f"[{args.scenario}] baseline {c['baseline_tokens']} tok "
            f"(score {c['baseline_score']}) | "
            f"overlord {c['overlord_tokens']} tok (score {c['overlord_score']}) | "
            f"saved {c['token_savings_pct']}%"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
