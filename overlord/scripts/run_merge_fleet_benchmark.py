#!/usr/bin/env python3
"""Compare six-agent Haiku merge thrashing vs Overlord fleet arbitration."""

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

from agents.merge_fleet_harness import (  # noqa: E402
    get_merge_fleet_scenario_names,
    run_merge_fleet_benchmark,
)
from agents.merge_fleet_report import write_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Six-agent merge fleet benchmark")
    parser.add_argument(
        "--scenario",
        default="merge_conflict_fleet",
        choices=get_merge_fleet_scenario_names(),
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
        os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

    result = run_merge_fleet_benchmark(args.scenario)
    md_path, json_path = write_report(result, args.output_dir)

    c = result["comparison"]
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(
        f"[{args.scenario}] baseline {c['baseline_cost_display']} / "
        f"{c['baseline_resolution_time_ms']} ms "
        f"({c['baseline_merge_fix_calls']} merge-fix) | "
        f"overlord {c['overlord_cost_display']} / "
        f"{c['overlord_resolution_time_ms']} ms "
        f"({c['overlord_arbitration_calls']} arbitration) | "
        f"saved {c['cost_savings_pct']}% cost, {c['time_savings_pct']}% time, "
        f"score {c['baseline_mean_score']}% → {c['overlord_mean_score']}%"
    )

    if args.json:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
