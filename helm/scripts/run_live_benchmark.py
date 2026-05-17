#!/usr/bin/env python3
"""Run live merge benchmark from the command line."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

env_path = ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=True)
    except ImportError:
        pass

for p in (BACKEND, ROOT):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from agents.live_harness import run_benchmark  # noqa: E402
from agents.merge_report import write_report  # noqa: E402
from agents.merge_scenarios import get_pairwise_merge_scenario_names  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Live merge benchmark")
    parser.add_argument(
        "--scenario",
        default="merge_conflict",
        choices=get_pairwise_merge_scenario_names(),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run every merge scenario",
    )
    parser.add_argument(
        "--seed-mode",
        choices=["scenario", "haiku"],
        default=None,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "experiments" / "results",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON to stdout")
    parser.add_argument("--mock", action="store_true", help="Use mock Bedrock")
    args = parser.parse_args()

    if args.mock:
        os.environ["HELM_MOCK_BEDROCK"] = "1"

    scenarios = get_pairwise_merge_scenario_names() if args.all else [args.scenario]
    results: list[dict] = []

    for name in scenarios:
        result = run_benchmark(name, seed_mode=args.seed_mode)
        md_path, json_path = write_report(result, args.output_dir)
        results.append(result)
        c = result["comparison"]
        print(f"Wrote {md_path}")
        print(f"Wrote {json_path}")
        print(
            f"[{name}] baseline {c['baseline_cost_display']} / {c['baseline_resolution_time_ms']} ms "
            f"(score {c['baseline_score']}, {result['baseline']['rounds']} rounds) | "
            f"helm {c['helm_cost_display']} / {c['helm_resolution_time_ms']} ms "
            f"(score {c['helm_score']}) | "
            f"saved {c['cost_savings_pct']}% cost, {c['time_savings_pct']}% time"
        )

    if args.json and len(results) == 1:
        print(json.dumps(results[0], indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
