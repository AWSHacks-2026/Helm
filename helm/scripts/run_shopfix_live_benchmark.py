#!/usr/bin/env python3
"""ShopFix LIVE benchmark: real git + real Bedrock. Refuses mock unless --allow-mock."""
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

from agents.shopfix_live_benchmark import (  # noqa: E402
    format_summary,
    run_shopfix_live_pair,
)


def _post_benchmark_checkpoint(suite: str, agent_count: int, pair: dict) -> None:
    """Notify Helm UI live session (best-effort)."""
    import urllib.error
    import urllib.request

    api = os.getenv("SHOPFIX_HELM_API", "http://127.0.0.1:8000").rstrip("/")
    session_id = os.getenv("HELM_TEAM_SESSION", "mergeai-hackathon-demo")
    helm = pair.get("helm") or {}
    comparison = pair.get("comparison") or {}
    detail = json.dumps(
        {
            "suite": suite,
            "agent_count": agent_count,
            "cost_savings_pct": comparison.get("cost_savings_pct"),
            "wall_savings_pct": comparison.get("wall_savings_pct"),
            "helm_agents_executed": helm.get("full_implementation_runs"),
        }
    )
    body = json.dumps(
        {
            "session_id": session_id,
            "agent_id": "shopfix-benchmark",
            "event": "benchmark_complete",
            "detail": detail,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{api}/history/checkpoint",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=3)
    except (urllib.error.URLError, TimeoutError):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="ShopFix live git + Bedrock benchmark")
    parser.add_argument("--suite", choices=["disjoint", "contention", "all"], default="all")
    parser.add_argument("--agents", default=os.getenv("SHOPFIX_AGENT_COUNTS", "2,4"))
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Allow HELM_MOCK_BEDROCK=1 (not authentic metrics)",
    )
    parser.add_argument("--keep-sandbox", action="store_true")
    args = parser.parse_args()

    if os.getenv("HELM_MOCK_BEDROCK", "0") == "1" and not args.allow_mock:
        print(
            "ERROR: HELM_MOCK_BEDROCK=1 — set HELM_MOCK_BEDROCK=0 for real AWS numbers "
            "or pass --allow-mock for smoke only.",
            file=sys.stderr,
        )
        return 2

    if args.keep_sandbox:
        os.environ["SHOPFIX_KEEP_SANDBOX"] = "1"

    counts = [int(x.strip()) for x in args.agents.split(",") if x.strip()]
    suites = ["disjoint", "contention"] if args.suite == "all" else [args.suite]
    results: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="shopfix-live-") as tmp:
        base = Path(tmp)
        for suite in suites:
            for n in counts:
                print(f"\n=== {suite} N={n} ===", flush=True)
                pair = run_shopfix_live_pair(suite, n, base / f"{suite}-n{n}")
                print(format_summary(pair), flush=True)
                results.append(pair)
                _post_benchmark_checkpoint(suite, n, pair)

    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"shopfix_live_{stamp}.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mock_bedrock": os.getenv("HELM_MOCK_BEDROCK", "0") == "1",
        "gate_enabled": os.getenv("HELM_GATE_ENABLED", "1") == "1",
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
