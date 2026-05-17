#!/usr/bin/env python3
"""Compare unchecked destructive action vs Overlord guardrail preflight."""

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

os.environ["OVERLORD_USE_LOCAL_MEMORY"] = "true"
os.environ["OVERLORD_USE_LOCAL_POLICY"] = "true"

from agents.guardrail_harness import (  # noqa: E402
    run_guardrail_benchmark,
    run_guardrail_fleet_benchmark,
)
from agents.guardrail_report import write_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Overlord guardrail benchmark")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments" / "results")
    parser.add_argument("--json", action="store_true", help="Print full JSON to stdout")
    parser.add_argument("--mock", action="store_true", help="Use mock Bedrock")
    parser.add_argument(
        "--fleet",
        action="store_true",
        help="Run five-agent fleet scenario (Sonnet tier)",
    )
    args = parser.parse_args()

    if args.mock:
        os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

    if args.fleet:
        result = run_guardrail_fleet_benchmark()
        md_path, json_path = write_report(result, args.output_dir)
        o = result["overlord"]
        print(f"Wrote {md_path}")
        print(f"Wrote {json_path}")
        print(
            f"[guardrail_fleet] agents={result.get('agent_count')} | "
            f"tier={o.get('resolution_tier')} | "
            f"cost={o['usage']['estimated_cost_display']} / {o['resolution_time_ms']} ms | "
            f"blocked={not o['preflight_allowed']}"
        )
    else:
        result = run_guardrail_benchmark()
        md_path, json_path = write_report(result, args.output_dir)
        c = result["comparison"]
        print(f"Wrote {md_path}")
        print(f"Wrote {json_path}")
        print(
            f"[guardrail_prevention] baseline {c['baseline_cost_display']} / "
            f"{c['baseline_resolution_time_ms']} ms | "
            f"overlord {c['overlord_cost_display']} / "
            f"{c['overlord_resolution_time_ms']} ms ({c.get('resolution_tier')}) | "
            f"blocked={c.get('overlord_blocked_action')}"
        )

    if args.json:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
