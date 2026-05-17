#!/usr/bin/env python3
"""Run ShopFix git benchmarks: baseline vs Helm across suites and agent counts."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agents.shopfix_harness import evaluate_gates, run_shopfix_case  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="ShopFix git benchmark")
    parser.add_argument("--suite", choices=["disjoint", "contention", "all"], default="all")
    parser.add_argument("--agents", default=os.getenv("SHOPFIX_AGENT_COUNTS", "2,4"))
    parser.add_argument("--mock", action="store_true", help="Set HELM_MOCK_BEDROCK=1")
    args = parser.parse_args()

    if args.mock:
        os.environ["HELM_MOCK_BEDROCK"] = "1"
        os.environ.setdefault("HELM_GATE_ENABLED", "1")

    counts = [int(x.strip()) for x in args.agents.split(",") if x.strip()]
    suites = ["disjoint", "contention"] if args.suite == "all" else [args.suite]
    rows = []

    with tempfile.TemporaryDirectory(prefix="shopfix-bench-") as tmp:
        base = Path(tmp)
        for suite in suites:
            for n in counts:
                for mode in ("baseline", "helm"):
                    rows.append(
                        run_shopfix_case(
                            suite=suite,
                            agent_count=n,
                            mode=mode,
                            work_dir=base / f"{suite}-n{n}-{mode}",
                            use_patches=False,
                        )
                    )

    gates = evaluate_gates(rows)
    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"shopfix_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    payload = {"rows": rows, "gates": gates}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(json.dumps(gates, indent=2))
    return 0 if gates.get("all_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
