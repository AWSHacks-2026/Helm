#!/usr/bin/env python3
"""Compare baseline duplicate agent work vs Helm deduplication."""

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

from agents.dedup_harness import get_dedup_scenario_names, run_dedup_benchmark  # noqa: E402
from agents.dedup_report import write_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Helm deduplication benchmark")
    parser.add_argument(
        "--scenario",
        default="duplicate_work_fleet",
        choices=get_dedup_scenario_names(),
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

    result = run_dedup_benchmark(args.scenario)
    md_path, json_path = write_report(result, args.output_dir)

    c = result["comparison"]
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(
        f"[{args.scenario}] baseline {c['baseline_cost_display']} / "
        f"{c['baseline_resolution_time_ms']} ms "
        f"({c['baseline_full_implementation_runs']} full impls) | "
        f"helm {c['helm_cost_display']} / "
        f"{c['helm_resolution_time_ms']} ms "
        f"({c['helm_full_implementation_runs']} full impls) | "
        f"saved {c['cost_savings_pct']}% cost "
        f"({c['baseline_tokens']}→{c['helm_tokens']} tok), "
        f"{c['duplicate_implementations_avoided']} duplicate impl(s) avoided"
    )

    if args.json:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
