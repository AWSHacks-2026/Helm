#!/usr/bin/env python3
"""Export all experiment JSON reports plus harness summaries to CSV."""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
RESULTS = ROOT / "experiments" / "results"
OUTPUT = RESULTS / "experiment_results.csv"

sys.path.insert(0, str(BACKEND))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        pass


def _benchmark_type(filename: str, data: dict) -> str:
    if filename.startswith("dedup_report"):
        return "dedup"
    if filename.startswith("merge_fleet_report"):
        return "merge_fleet"
    if filename.startswith("merge_report"):
        return "merge_pairwise"
    if filename.startswith("intent_report"):
        return "intent"
    if filename.startswith("guardrail_report"):
        return "guardrail"
    scenario = data.get("scenario", "")
    if scenario == "intent_conflict":
        return "intent"
    if scenario == "guardrail_prevention":
        return "guardrail"
    return "unknown"


def _row_from_comparison_report(path: Path, data: dict) -> dict[str, object]:
    c = data.get("comparison") or {}
    b = data.get("baseline") or {}
    o = data.get("helm") or {}
    b_usage = b.get("usage") or {}
    o_usage = o.get("usage") or {}

    row: dict[str, object] = {
        "report_file": path.name,
        "benchmark_type": _benchmark_type(path.name, data),
        "scenario": data.get("scenario", ""),
        "session_id": data.get("session_id", ""),
        "mock_bedrock": data.get("mock_bedrock", ""),
        "seed_mode": data.get("seed_mode", ""),
        "agent_count": data.get("agent_count", ""),
        "baseline_path": b.get("path", ""),
        "helm_path": o.get("path", ""),
        "baseline_tokens": c.get("baseline_tokens", b_usage.get("total_tokens", "")),
        "helm_tokens": c.get("helm_tokens", o_usage.get("total_tokens", "")),
        "token_savings_pct": c.get("token_savings_pct", ""),
        "baseline_cost_usd": c.get("baseline_cost_usd", b_usage.get("estimated_cost_usd", "")),
        "helm_cost_usd": c.get("helm_cost_usd", o_usage.get("estimated_cost_usd", "")),
        "baseline_cost_display": c.get("baseline_cost_display", b_usage.get("estimated_cost_display", "")),
        "helm_cost_display": c.get("helm_cost_display", o_usage.get("estimated_cost_display", "")),
        "cost_savings_pct": c.get("cost_savings_pct", ""),
        "helm_beats_cost": c.get("helm_beats_cost", ""),
        "baseline_resolution_time_ms": c.get(
            "baseline_resolution_time_ms", b.get("resolution_time_ms", "")
        ),
        "helm_resolution_time_ms": c.get(
            "helm_resolution_time_ms", o.get("resolution_time_ms", "")
        ),
        "time_savings_pct": c.get("time_savings_pct", ""),
        "helm_beats_time": c.get("helm_beats_time", ""),
        "baseline_mean_score": c.get("baseline_mean_score", b.get("mean_score", "")),
        "helm_mean_score": c.get("helm_mean_score", o.get("mean_score", "")),
        "baseline_passed_all": c.get("baseline_passed_all", b.get("passed_all", "")),
        "helm_passed_all": c.get("helm_passed_all", o.get("passed_all", "")),
        "helm_beats_quality": c.get("helm_beats_quality", ""),
        "baseline_score": c.get("baseline_score", b.get("evaluation", {}).get("score", "")),
        "helm_score": c.get("helm_score", o.get("evaluation", {}).get("score", "")),
        "baseline_passed": c.get("baseline_passed", b.get("evaluation", {}).get("passed", "")),
        "helm_passed": c.get("helm_passed", o.get("evaluation", {}).get("passed", "")),
        "helm_beats_tokens": c.get("helm_beats_tokens", ""),
        "merge_fleet_strategy": o.get("strategy", data.get("token_limits", {}).get("strategy", "")),
        "baseline_merge_fix_calls": c.get("baseline_merge_fix_calls", b.get("merge_fix_calls", "")),
        "helm_arbitration_calls": c.get(
            "helm_arbitration_calls", o.get("arbitration_calls", "")
        ),
        "merge_fix_calls_avoided": c.get("merge_fix_calls_avoided", ""),
        "baseline_full_impl_runs": c.get(
            "baseline_full_implementation_runs", b.get("full_implementation_runs", "")
        ),
        "helm_full_impl_runs": c.get(
            "helm_full_implementation_runs", o.get("full_implementation_runs", "")
        ),
        "duplicate_impls_avoided": c.get("duplicate_implementations_avoided", ""),
        "helm_duplicate_detected": c.get("helm_duplicate_detected", ""),
        "helm_stops_conflict": c.get("helm_stops_conflict", ""),
        "helm_blocked_action": c.get("helm_blocked_action", ""),
        "blocked_rule": c.get("blocked_rule", ""),
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return row


def collect_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for path in sorted(RESULTS.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if "comparison" in data and ("baseline" in data or "helm" in data):
            rows.append(_row_from_comparison_report(path, data))

    return rows


def write_csv(rows: list[dict[str, object]], out_path: Path) -> None:
    if not rows:
        raise SystemExit("No experiment rows to export")

    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    _load_dotenv()
    rows = collect_rows()
    write_csv(rows, OUTPUT)
    print(f"Wrote {len(rows)} rows to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
