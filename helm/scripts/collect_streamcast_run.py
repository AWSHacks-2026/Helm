#!/usr/bin/env python3
"""Collect Streamcast benchmark metrics into results/<run_id>/report.json."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.collector import collect_run  # noqa: E402
from benchmarks.report import write_comparison  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Streamcast benchmark run metrics")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--compare", nargs=2, metavar=("BASELINE_RUN", "HELM_RUN"))
    args = parser.parse_args()

    results_dir = ROOT / "benchmarks" / "results"
    meta_path = results_dir / args.run_id / "meta.json"
    if not meta_path.exists():
        raise SystemExit(f"Unknown run: {args.run_id} (missing {meta_path})")

    import json

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    session_id = meta.get("session_id", args.run_id)
    repo_root = Path(meta["repo_root"]) if meta.get("repo_root") else None

    report = collect_run(
        run_id=args.run_id,
        results_dir=results_dir,
        api_base=args.api,
        session_id=session_id,
        integration_repo=repo_root,
    )
    print(f"Wrote {results_dir / args.run_id / 'report.json'}")
    print(f"  suite={report.suite} helm_enabled={report.helm_enabled} wall_clock={report.wall_clock_seconds:.1f}s")

    if args.compare:
        path = write_comparison(results_dir, args.compare[0], args.compare[1])
        print(f"Comparison report: {path}")


if __name__ == "__main__":
    main()
