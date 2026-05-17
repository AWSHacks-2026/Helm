"""Human-readable report for live merge benchmarks."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def render_markdown(result: dict[str, Any]) -> str:
    c = result["comparison"]
    b = result["baseline"]
    o = result["overlord"]
    time_savings = c.get("time_savings_pct")
    time_line = (
        f"| Wall time (ms) | {c.get('baseline_resolution_time_ms', '—')} | "
        f"{c.get('overlord_resolution_time_ms', '—')} | {time_savings}% |"
        if time_savings is not None
        else ""
    )
    lines = [
        "# Merge conflict benchmark",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Scenario: `{result['scenario']}`",
        f"Seed mode: `{result.get('seed_mode', 'scenario')}`",
        f"Mode: {'mock' if result.get('mock_bedrock') else 'live Bedrock'}",
        "",
        "## Summary",
        "",
        "| Metric | Baseline (2× Haiku thrash) | With Overlord | Savings |",
        "|--------|----------------------------|---------------|---------|",
        f"| **Est. cost (USD)** | {c['baseline_cost_display']} | {c['overlord_cost_display']} | {c['cost_savings_pct']}% |",
        f"| Total tokens (detail) | {c['baseline_tokens']} | {c['overlord_tokens']} | {c['token_savings_pct']}% |",
    ]
    if time_line:
        lines.append(time_line)
    lines.extend(
        [
            f"| Quality score | {c['baseline_score']}% | {c['overlord_score']}% | — |",
            f"| Passed acceptance | {c['baseline_passed']} | {c['overlord_passed']} | — |",
            f"| Merge-fix rounds | {b['rounds']} | {o['rounds']} | — |",
            "",
            f"**Overlord wins on cost:** {c['overlord_beats_cost']}",
            f"**Overlord wins on quality:** {c['overlord_beats_quality']}",
            f"_Token counts alone mislead when Overlord uses Sonnet vs Haiku — compare USD._",
            "",
            "## What each path did",
            "",
            "### Baseline (no Overlord)",
            "- Two Haiku agents alternate `merge_fix` rounds until acceptance passes or max rounds.",
            f"- Rounds used: **{b['rounds']}** (max {result.get('max_rounds', 3)})",
            "",
            "### Overlord",
            "- One Sonnet arbitration call produces merged `resolved_code`.",
            f"- Rounds: **{o['rounds']}**",
            "",
            "### Reasoning",
            "",
            (o.get("resolution") or {}).get("reasoning") or "—",
            "",
        ]
    )
    if c.get("cost_note"):
        lines.append(f"_{c['cost_note']}_")
        lines.append("")
    return "\n".join(lines)


def write_report(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    import json

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    scenario = result["scenario"]
    md_path = output_dir / f"merge_report_{scenario}_{stamp}.md"
    json_path = output_dir / f"merge_report_{scenario}_{stamp}.json"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return md_path, json_path
