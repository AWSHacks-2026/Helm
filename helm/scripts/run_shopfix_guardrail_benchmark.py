#!/usr/bin/env python3
"""ShopFix real git: destructive edit vs guardrail preflight (live AWS)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

env_path = ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        pass

for p in (BACKEND, ROOT):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from agents.shopfix_guardrail_benchmark import (  # noqa: E402
    format_shopfix_guardrail_summary,
    run_shopfix_guardrail_benchmark,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="ShopFix guardrail benchmark")
    parser.add_argument("--allow-mock", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip pytest after baseline destructive path",
    )
    args = parser.parse_args()

    if os.getenv("HELM_MOCK_BEDROCK", "0") == "1" and not args.allow_mock:
        print(
            "ERROR: set HELM_MOCK_BEDROCK=0 for live metrics or pass --allow-mock",
            file=sys.stderr,
        )
        return 2

    os.environ.setdefault("HELM_USE_LOCAL_MEMORY", "true")
    os.environ.setdefault("HELM_USE_LOCAL_POLICY", "true")
    if args.skip_verify:
        os.environ["SHOPFIX_SKIP_VERIFY"] = "1"

    result = run_shopfix_guardrail_benchmark(skip_verify=args.skip_verify)
    print(format_shopfix_guardrail_summary(result), flush=True)

    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"shopfix_guardrail_{stamp}.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **result,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    if args.json:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
