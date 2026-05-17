from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def format_cell_row(cell: dict[str, Any]) -> str:
    c = cell.get("comparison", {})
    return (
        f"| {cell.get('app')} | {cell.get('suite')} | {cell.get('agent_count')} | "
        f"{c.get('baseline_cost_display', '—')} | {c.get('helm_cost_display', '—')} | "
        f"{c.get('cost_savings_pct', 0)}% | {c.get('baseline_seconds', 0)}s | "
        f"{c.get('helm_seconds', 0)}s | {c.get('time_savings_pct', 0)}% | "
        f"{c.get('baseline_tests_pass')} | {c.get('helm_tests_pass')} |"
    )


def write_matrix_report(results: list[dict[str, Any]], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"live_matrix_{stamp}.json"
    md_path = out_dir / "LIVE_MATRIX_RESULTS.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cells": results,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    header = (
        "# Live matrix benchmark results\n\n"
        "| App | Suite | N | Baseline $ | Helm $ | Cost Δ | Baseline time | Helm time | Time Δ | Base tests | Helm tests |\n"
        "|-----|-------|---|------------|--------|--------|---------------|-----------|--------|------------|------------|\n"
    )
    rows = "\n".join(format_cell_row(r) for r in results)
    md_path.write_text(header + rows + "\n", encoding="utf-8")
    return json_path
