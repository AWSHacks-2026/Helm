"""Human-readable report for deduplication benchmarks."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def render_markdown(result: dict[str, Any]) -> str:
    c = result["comparison"]
    b = result["baseline"]
    o = result["overlord"]
    agent_count = result.get("agent_count", 2)
    limits = result.get("token_limits") or {}
    lines = [
        "# Overlord deduplication benchmark",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Scenario: `{result['scenario']}`",
        f"Agents: **{agent_count}**",
        f"Mode: {'mock' if result.get('mock_bedrock') else 'live Bedrock'}",
    ]
    if limits:
        lines.append(
            f"Token caps: continuations **{limits.get('continuation_max_tokens', '—')}**, "
            f"reassignments **{limits.get('reassign_max_tokens', '—')}**"
        )
    lines.extend(
        [
        "",
        "## Summary",
        "",
        "| Metric | Baseline (no Overlord) | With Overlord | Savings |",
        "|--------|------------------------|---------------|---------|",
        f"| **Est. cost (USD)** | {c['baseline_cost_display']} | {c['overlord_cost_display']} | {c['cost_savings_pct']}% |",
        f"| Total tokens (detail) | {c['baseline_tokens']:,} | {c['overlord_tokens']:,} | {c['token_savings_pct']}% |",
        f"| Resolution time (ms) | {c['baseline_resolution_time_ms']} | {c['overlord_resolution_time_ms']} | {c['time_savings_pct']}% |",
        f"| Primary implementation runs | {c['baseline_full_implementation_runs']} | {c['overlord_full_implementation_runs']} | {c['duplicate_implementations_avoided']} avoided |",
        "",
        f"**Duplicate detected by Overlord:** {c['overlord_duplicate_detected']}",
        "",
        "_Cost uses Bedrock on-demand rates: Haiku ~$1/$5 per MTok, Sonnet ~$3/$15 per MTok (input/output)._",
        "",
        ]
    )
    if c.get("cost_note"):
        lines.append(f"_{c['cost_note']}_")
        lines.append("")
    lines.extend(
        [
        "## What each path did",
        "",
        "### Baseline",
        f"- All **{agent_count}** agents ran a full Haiku implementation on their assigned files.",
        f"- Primary implementation runs: **{b['full_implementation_runs']}**",
        "",
        "### Overlord",
        "- One Sonnet call coordinates all agents (fleet) or pairwise dedup for 2-agent scenarios.",
        ]
    )

    if o.get("continuations"):
        lines.extend(
            [
                f"- Agents continuing primary work: **{', '.join(o['continuations'])}**",
                "",
                "#### Reassignments",
                "",
            ]
        )
        for item in o.get("reassignments", []):
            lines.append(
                f"- **{item['agent_id']}** → {item.get('suggested_new_task', '—')}"
            )
    else:
        lines.extend(
            [
                f"- Agent continuing: **{o.get('agent_to_continue', '—')}**",
                f"- Agent reassigned: **{o.get('agent_to_reassign', '—')}**",
                f"- New task: {o.get('suggested_new_task', '—')}",
            ]
        )

    lines.extend(
        [
            "",
            f"- Primary implementation runs: **{o['full_implementation_runs']}**",
            "",
            "### Reasoning",
            "",
            o.get("reasoning") or "—",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    import json

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    md_path = output_dir / f"dedup_report_{stamp}.md"
    json_path = output_dir / f"dedup_report_{stamp}.json"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return md_path, json_path
