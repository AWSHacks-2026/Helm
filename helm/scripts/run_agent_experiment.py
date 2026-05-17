#!/usr/bin/env python3
"""Run multi-agent conflict experiments (no Helm) and write a report."""

from __future__ import annotations

import argparse
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

from experiments.runner import run_all_themes
from experiments.report import write_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run themed multi-agent experiments")
    parser.add_argument(
        "--themes",
        nargs="*",
        help="Theme folder names (default: all under experiments/themes)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock Haiku (no Bedrock cost)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "experiments" / "results",
    )
    args = parser.parse_args()

    if args.mock:
        os.environ["HELM_MOCK_BEDROCK"] = "1"

    results = run_all_themes(theme_names=args.themes or None, mock=args.mock)
    out_dir = args.output_dir
    md_path, json_path = write_report(results, out_dir, mock=args.mock)
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
