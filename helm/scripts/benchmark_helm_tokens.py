#!/usr/bin/env python3
"""Run the live Helm token benchmark demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
for path in (BACKEND, ROOT):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

env_path = ROOT / ".env.local"
if env_path.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        pass

from agents.token_benchmark import (  # noqa: E402
    AGENT_COUNTS,
    REALISTIC_OVERLAP_PROFILE,
    WORST_CASE_PROFILE,
    BenchmarkConfig,
    print_summary_table,
    run_benchmark_matrix,
    save_benchmark_figure,
    write_results_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark real token usage with and without Helm."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "demo",
        help="Directory for benchmark JSON and PNG outputs.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=700,
        help="Max output tokens per Haiku baseline conflict call.",
    )
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Allow HELM_MOCK_BEDROCK=1 for local test runs only.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable tqdm progress bars.",
    )
    parser.add_argument(
        "--profile",
        choices=(REALISTIC_OVERLAP_PROFILE, WORST_CASE_PROFILE),
        default=REALISTIC_OVERLAP_PROFILE,
        help="Conflict model to benchmark.",
    )
    args = parser.parse_args()

    config = BenchmarkConfig(
        agent_counts=AGENT_COUNTS,
        output_dir=args.output_dir,
        max_tokens=args.max_tokens,
        allow_mock=args.allow_mock,
        show_progress=not args.no_progress,
        profile=args.profile,
    )
    rows = run_benchmark_matrix(config)
    print_summary_table(rows)
    json_path = write_results_json(rows, config.output_dir, profile=config.profile)
    figure_path = save_benchmark_figure(rows, config.output_dir, profile=config.profile)
    print(f"Wrote {json_path}")
    print(f"Wrote {figure_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
