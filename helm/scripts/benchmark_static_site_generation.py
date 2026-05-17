#!/usr/bin/env python3
"""Generate browser-runnable static commerce sites with and without Helm."""

from __future__ import annotations

import argparse
import logging
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

from agents.static_site_benchmark import (  # noqa: E402
    DEFAULT_STATIC_OUTPUT_DIR,
    DEFAULT_RICH_STATIC_OUTPUT_DIR,
    STATIC_AGENT_COUNTS,
    StaticSiteConfig,
    print_static_summary_table,
    run_static_site_benchmark,
    save_static_benchmark_figure,
    write_static_benchmark_results,
)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and score static commerce sites with and without Helm."
    )
    parser.add_argument(
        "--agent-counts",
        type=int,
        nargs="+",
        default=list(STATIC_AGENT_COUNTS),
        help="Agent counts to generate. Defaults to 2 4 8.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated static commerce sites.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Max output tokens per generation call.",
    )
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Allow HELM_MOCK_BEDROCK=1 for local smoke tests.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable tqdm progress bars.",
    )
    parser.add_argument(
        "--quality-mode",
        choices=("standard", "rich"),
        default="standard",
        help="Use standard low-cost generation or rich higher-token app generation.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Logging verbosity for benchmark timing/token diagnostics.",
    )
    args = parser.parse_args()
    configure_logging(args.log_level)
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = (
            DEFAULT_RICH_STATIC_OUTPUT_DIR
            if args.quality_mode == "rich"
            else DEFAULT_STATIC_OUTPUT_DIR
        )

    config = StaticSiteConfig.for_quality_mode(
        args.quality_mode,
        agent_counts=tuple(args.agent_counts),
        output_dir=output_dir,
        allow_mock=args.allow_mock,
        show_progress=not args.no_progress,
    )
    if args.max_tokens is not None:
        config = StaticSiteConfig(
            agent_counts=config.agent_counts,
            output_dir=config.output_dir,
            max_tokens=args.max_tokens,
            allow_mock=config.allow_mock,
            show_progress=config.show_progress,
            quality_mode=config.quality_mode,
        )
    results = run_static_site_benchmark(config)
    print_static_summary_table(results)
    results_path = write_static_benchmark_results(results, config.output_dir)
    figure_path = save_static_benchmark_figure(results, config.output_dir)
    print(f"Wrote {results_path}")
    print(f"Wrote {figure_path}")
    view_count = max(config.agent_counts)
    print(
        "View a site with: "
        f"python -m http.server 5174 --directory {config.output_dir / 'with-helm' / f'N{view_count}'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
