"""Write human-readable experiment reports."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiments.metrics import ThemeRunResult, summarize_run


def render_markdown(results: list[dict[str, Any]], run_meta: dict[str, Any]) -> str:
    lines = [
        "# Agent conflict experiment report",
        "",
        f"Generated: {run_meta.get('generated_at', datetime.now(timezone.utc).isoformat())}",
        f"Mode: {'mock Haiku' if run_meta.get('mock') else 'live Bedrock (if configured)'}",
        f"Themes: {len(results)}",
        "",
        "## Summary metrics",
        "",
        "| Theme | Conflict edits | Reverted commits | Total tokens | Time (ms) | Successful build |",
        "|-------|----------------|------------------|--------------|-----------|-------------------|",
    ]

    total_conflicts = 0
    total_reverts = 0
    total_tokens = 0
    total_ms = 0

    for row in results:
        lines.append(
            f"| {row['theme']} | {row['conflict_edits']} | {row['reverted_commits']} | "
            f"{row['total_tokens']} | {row['resolution_time_ms']} | "
            f"{row['successful_build_rate']:.0%} |"
        )
        total_conflicts += row["conflict_edits"]
        total_reverts += row["reverted_commits"]
        total_tokens += row["total_tokens"]
        total_ms += row["resolution_time_ms"]

    lines.extend(
        [
            "",
            f"| **Total** | **{total_conflicts}** | **{total_reverts}** | **{total_tokens}** | **{total_ms}** | — | — |",
            "",
            "## Per theme",
            "",
        ]
    )

    for row in results:
        lines.extend(
            [
                f"### {row['theme']}",
                "",
                f"- Conflict edits (different agent outputs on same file): **{row['conflict_edits']}**",
                f"- Reverted commits (sequential apply, beta overwrote alpha): **{row['reverted_commits']}**",
                f"- Total tokens (all agents): **{row['total_tokens']}**",
                f"- Wall time (all agent calls): **{row['resolution_time_ms']} ms**",
                f"- Successful build rate (merged files parse after sequential apply): **{row['successful_build_rate']:.0%}**",
                f"- Per-agent syntax success: **{row['agent_success_rate']:.0%}**",
                "",
                "#### Agents",
                "",
                "| Agent | Runs | Tokens | Success rate |",
                "|-------|------|--------|----------------|",
            ]
        )
        for aid, stats in row.get("agents", {}).items():
            lines.append(
                f"| {aid} | {stats['runs']} | {stats['tokens']} | {stats['success_rate']:.0%} |"
            )
        lines.append("")
    return "\n".join(lines)


def write_report(
    results: list[ThemeRunResult],
    output_dir: Path,
    *,
    mock: bool = False,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_meta = {"generated_at": datetime.now(timezone.utc).isoformat(), "mock": mock}
    summaries = [summarize_run(r) for r in results]
    md = render_markdown(summaries, run_meta)
    md_path = output_dir / f"report_{stamp}.md"
    md_path.write_text(md, encoding="utf-8")

    import json

    json_path = output_dir / f"report_{stamp}.json"
    json_path.write_text(
        json.dumps({"meta": run_meta, "themes": summaries}, indent=2),
        encoding="utf-8",
    )
    return md_path, json_path
