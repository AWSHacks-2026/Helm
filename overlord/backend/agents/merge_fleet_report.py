"""Human-readable report for six-agent merge fleet benchmarks."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bedrock.cost_estimate import format_usd


def _bar(label: str, value: int, max_value: int, width: int = 28) -> str:
    if max_value <= 0:
        filled = 0
    else:
        filled = min(width, int(width * value / max_value))
    return f"{label.ljust(14)} |{'█' * filled}{'░' * (width - filled)}| {value:,}"


def _bar_cost(label: str, value_usd: float, max_usd: float, width: int = 28) -> str:
    max_usd = max(max_usd, 1e-9)
    filled = min(width, int(width * value_usd / max_usd))
    return f"{label.ljust(14)} |{'█' * filled}{'░' * (width - filled)}| {format_usd(value_usd)}"


def render_markdown(result: dict[str, Any]) -> str:
    c = result["comparison"]
    b = result["baseline"]
    o = result["overlord"]
    agent_count = result.get("agent_count", 6)
    limits = result.get("token_limits") or {}
    max_cost = max(c["baseline_cost_usd"], c["overlord_cost_usd"], 1e-9)
    max_ms = max(c["baseline_resolution_time_ms"], c["overlord_resolution_time_ms"], 1)

    lines = [
        "# Merge conflict fleet benchmark (6 agents)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Scenario: `{result['scenario']}`",
        f"Agents: **{agent_count}** across auth, catalog, and billing",
        f"Mode: {'mock' if result.get('mock_bedrock') else 'live Bedrock'}",
    ]
    if limits:
        lines.append(f"Haiku / Sonnet output cap: **{limits.get('merge_max_tokens', '—')}** tokens")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Metric | Baseline (Haiku merge chain) | With Overlord | Savings |",
            "|--------|------------------------------|---------------|---------|",
            f"| **Est. cost (USD)** | {c['baseline_cost_display']} | {c['overlord_cost_display']} | {c['cost_savings_pct']}% |",
            f"| Total tokens (detail) | {c['baseline_tokens']:,} | {c['overlord_tokens']:,} | {c['token_savings_pct']}% |",
            f"| Wall time (ms) | {c['baseline_resolution_time_ms']:,} | {c['overlord_resolution_time_ms']:,} | {c['time_savings_pct']}% |",
            f"| Merge-fix / arbitration calls | {c['baseline_merge_fix_calls']} | {c['overlord_arbitration_calls']} | {c['merge_fix_calls_avoided']} avoided |",
            f"| Mean quality score | {c['baseline_mean_score']}% | {c['overlord_mean_score']}% | — |",
            f"| All files pass acceptance | {c['baseline_passed_all']} | {c['overlord_passed_all']} | — |",
            "",
            "## Comparison chart (cost & time)",
            "",
            "```",
            _bar_cost("Baseline $", c["baseline_cost_usd"], max_cost),
            _bar_cost("Overlord $", c["overlord_cost_usd"], max_cost),
            _bar("Baseline ms", c["baseline_resolution_time_ms"], max_ms),
            _bar("Overlord ms", c["overlord_resolution_time_ms"], max_ms),
            "```",
            "",
            "_Cost: Haiku ~$1/$5 and Sonnet ~$3/$15 per MTok (input/output). Sonnet arbitration costs more per token but avoids Haiku merge thrash._",
            "",
            "## Flow",
            "",
            "```mermaid",
            "flowchart TB",
            "  subgraph baseline [Baseline: no Overlord]",
            "    A1[agent_a code] --> A2[agent_b merge_fix]",
            "    A2 --> A3[agent_c merge_fix]",
            "    D1[agent_d code] --> D2[agent_e merge_fix]",
            "    F1[agent_f only]",
            "  end",
            "  subgraph overlord [With Overlord]",
            "    S1[Sonnet merge auth] ~~~ S2[Sonnet merge catalog]",
            "    S1 --> R1[auth handlers.py]",
            "    S2 --> R2[catalog products.py]",
            "    R3[billing invoices.py]",
            "  end",
            "```",
            "",
            "## Per-file agents",
            "",
            "| File | Agents | Overlap |",
            "|------|--------|---------|",
            "| `app/auth/handlers.py` | agent_a, b, c | JWT vs sign-in vs session |",
            "| `app/catalog/products.py` | agent_d, e | search vs listing |",
            "| `app/billing/invoices.py` | agent_f | single agent |",
            "",
            "## What each path did",
            "",
            "### Baseline",
            f"- Sequential Haiku `merge_fix` on shared files (up to **{b['rounds_max']}** rounds per file).",
            f"- Total merge-fix calls: **{b['merge_fix_calls']}**",
            f"- Mean score: **{b['mean_score']}%**",
            "",
            "### Overlord",
            "- Parallel per-file Sonnet merge (`arbitrate_fleet`); billing passes through when only one agent.",
            f"- Arbitration calls: **{o['arbitration_calls']}**",
            f"- Mean score: **{o['mean_score']}%**",
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
    md_path = output_dir / f"merge_fleet_report_{stamp}.md"
    json_path = output_dir / f"merge_fleet_report_{stamp}.json"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return md_path, json_path
