"""Human-readable report for guardrail prevention benchmarks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def render_markdown(result: dict[str, Any]) -> str:
    o = result.get("helm") or {}
    if "comparison" not in result:
        usage = o.get("usage") or {}
        return "\n".join(
            [
                "# Helm guardrail fleet benchmark",
                "",
                f"Scenario: `{result.get('scenario', '')}`",
                f"Agents: **{result.get('agent_count', '—')}**",
                f"Mode: {'mock' if result.get('mock_bedrock') else 'live Bedrock'}",
                "",
                f"**Tier:** {o.get('resolution_tier', '—')}",
                f"**Cost:** {usage.get('estimated_cost_display', '—')}",
                f"**Time (ms):** {o.get('resolution_time_ms', '—')}",
                f"**Blocked:** {not o.get('preflight_allowed', True)}",
                f"**Rule:** {o.get('blocked_rule') or '—'}",
                "",
            ]
        )

    c = result["comparison"]
    o = result["helm"]
    return "\n".join(
        [
            "# Helm guardrail prevention benchmark",
            "",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            f"Scenario: `{result['scenario']}`",
            f"Mode: {'mock' if result.get('mock_bedrock') else 'live Bedrock'}",
            "",
            "## Summary",
            "",
            "| Metric | Baseline (unchecked delete + rebuild) | With Helm | Savings |",
            "|--------|---------------------------------------|---------------|---------|",
            f"| **Est. cost (USD)** | {c['baseline_cost_display']} | {c['helm_cost_display']} | {c['cost_savings_pct']}% |",
            f"| Total tokens | {c['baseline_tokens']:,} | {c['helm_tokens']:,} | {c['token_savings_pct']}% |",
            f"| Resolution time (ms) | {c['baseline_resolution_time_ms']} | {c['helm_resolution_time_ms']} | {c['time_savings_pct']}% |",
            "",
            f"**Baseline executed destructive action:** {c.get('baseline_executed')}",
            f"**Helm blocked preflight:** {c.get('helm_blocked_action')}",
            f"**Blocked rule:** {c.get('blocked_rule') or '—'}",
            f"**Verdict:** {o.get('verdict') or '—'}",
            f"**Resolution tier:** {c.get('resolution_tier') or o.get('resolution_tier') or '—'}",
            f"**Escalated to Sonnet:** {c.get('escalated_to_sonnet', o.get('escalated_to_sonnet'))}",
            "",
        ]
    )


def write_report(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    md_path = output_dir / f"guardrail_report_{stamp}.md"
    json_path = output_dir / f"guardrail_report_{stamp}.json"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return md_path, json_path
