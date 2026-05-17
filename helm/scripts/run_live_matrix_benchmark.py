#!/usr/bin/env python3
"""Unified live Bedrock benchmark: ShopFix + Streamcast × N × suite × baseline/helm."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agents.live_matrix.report import write_matrix_report  # noqa: E402
from agents.shopfix_live_benchmark import app_config as shopfix_config  # noqa: E402
from agents.shopfix_live_benchmark import format_summary as shopfix_summary  # noqa: E402
from agents.streamcast_live_benchmark import app_config as streamcast_config  # noqa: E402
from agents.live_matrix.engine import run_live_pair  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Live matrix benchmark (real Bedrock)")
    parser.add_argument("--apps", default="shopfix,streamcast", help="shopfix,streamcast")
    parser.add_argument("--agents", default=os.getenv("LIVE_MATRIX_AGENTS", "2"))
    parser.add_argument("--suites", default="contention,disjoint", help="order: contention first")
    parser.add_argument("--allow-mock", action="store_true")
    parser.add_argument("--keep-sandbox", action="store_true")
    parser.add_argument("--helm-api", default=os.getenv("HELM_API_BASE", "http://127.0.0.1:8000"))
    parser.add_argument(
        "--cells",
        default="",
        help="Filter one cell, e.g. shopfix:contention:2",
    )
    args = parser.parse_args()

    if os.getenv("HELM_MOCK_BEDROCK", "0") == "1" and not args.allow_mock:
        print(
            "ERROR: HELM_MOCK_BEDROCK=1 — set HELM_MOCK_BEDROCK=0 for real AWS or pass --allow-mock",
            file=sys.stderr,
        )
        return 2

    if args.keep_sandbox:
        os.environ["LIVE_MATRIX_KEEP_SANDBOX"] = "1"

    apps = [a.strip() for a in args.apps.split(",") if a.strip()]
    suites = [s.strip() for s in args.suites.split(",") if s.strip()]
    counts = [int(x.strip()) for x in args.agents.split(",") if x.strip()]

    app_configs = {
        "shopfix": shopfix_config(),
        "streamcast": streamcast_config(),
    }

    plan: list[tuple[str, str, int]] = []
    for app in apps:
        for suite in suites:
            for n in counts:
                key = f"{app}:{suite}:{n}"
                if args.cells and args.cells != key:
                    continue
                plan.append((app, suite, n))

    results: list[dict] = []
    bar = tqdm(plan, desc="matrix", unit="cell")
    with tempfile.TemporaryDirectory(prefix="live-matrix-") as tmp:
        base = Path(tmp)
        for app, suite, n in bar:
            bar.set_postfix(app=app, suite=suite, n=n)
            cfg = app_configs[app]
            work = base / f"{app}-{suite}-n{n}"
            pair = run_live_pair(cfg, suite, n, work, helm_api_base=args.helm_api)
            results.append(pair)
            if app == "shopfix":
                tqdm.write(shopfix_summary(pair))
            else:
                c = pair["comparison"]
                tqdm.write(
                    f"Streamcast LIVE — {suite} N={n} "
                    f"baseline={c['baseline_cost_display']} helm={c['helm_cost_display']}"
                )

    out_dir = ROOT / "experiments" / "results"
    json_path = write_matrix_report(results, out_dir)
    print(f"\nWrote {json_path}")
    print(f"Summary: {out_dir / 'LIVE_MATRIX_RESULTS.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
