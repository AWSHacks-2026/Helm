"""Human-readable report for intent conflict benchmarks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def render_markdown(result: dict[str, Any]) -> str:
    c = result["comparison"]
    o = result["overlord"]
    return "\n".join(
        [
            "# Overlord intent conflict benchmark",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Scenario: `{result['scenario']}`",
            f"Mode: {'mock' if result.get('mock_bedrock') else 'live Bedrock'}",
            "",
            "## Summary",
            "",
            "| Metric | Baseline (both agents implement) | With Overlord | Savings |",
            "|--------|----------------------------------|---------------|---------|",
            f"| **Est. cost (USD)** | {c['baseline_cost_display']} | {c['overlord_cost_display']} | {c['cost_savings_pct']}% |",
            f"| Total tokens | {c['baseline_tokens']:,} | {c['overlord_tokens']:,} | {c['token_savings_pct']}% |",
            f"| Resolution time (ms) | {c['baseline_resolution_time_ms']} | {c['overlord_resolution_time_ms']} | {c['time_savings_pct']}% |",
            "",
            f"**Conflict detected before code:** {c.get('overlord_stops_conflict', o.get('conflict_detected_before_code'))}",
            f"**Unified intent:** {o.get('unified_intent') or '—'}",
            "",
        ]
    )


def write_report(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    md_path = output_dir / f"intent_report_{stamp}.md"
    json_path = output_dir / f"intent_report_{stamp}.json"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return md_path, json_path
