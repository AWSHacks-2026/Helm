from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from benchmarks.collector import RunReport


def _pct_delta(baseline: float, helm: float) -> str:
    if baseline == 0:
        return "n/a"
    delta = ((helm - baseline) / baseline) * 100
    return f"{delta:+.1f}%"


def compare_reports(baseline: RunReport, helm_on: RunReport) -> tuple[str, bool]:
    rows = [
        ("Wall clock (s)", f"{baseline.wall_clock_seconds:.1f}", f"{helm_on.wall_clock_seconds:.1f}",
         _pct_delta(baseline.wall_clock_seconds, helm_on.wall_clock_seconds)),
        ("Helm API calls", str(baseline.helm_api_calls), str(helm_on.helm_api_calls),
         _pct_delta(float(baseline.helm_api_calls), float(helm_on.helm_api_calls))),
        ("Intents declared", str(baseline.intents_declared), str(helm_on.intents_declared), "—"),
        ("Guardrails blocked", str(baseline.guardrails_blocked), str(helm_on.guardrails_blocked), "—"),
        ("Git conflict files", str(baseline.git_conflict_files), str(helm_on.git_conflict_files),
         _pct_delta(float(baseline.git_conflict_files), float(helm_on.git_conflict_files))),
        ("Merge success", str(baseline.merge_success), str(helm_on.merge_success), "—"),
        ("Tokens saved", baseline.tokens_saved_display, helm_on.tokens_saved_display, "—"),
    ]
    header = "| Metric | Baseline (Helm OFF) | Helm ON | Δ |\n|--------|---------------------|---------|---|\n"
    body = "\n".join(f"| {m} | {a} | {b} | {d} |" for m, a, b, d in rows)

    passed = True
    verdict_lines: list[str] = []
    if baseline.suite == "independent":
        passed = (
            helm_on.helm_api_calls <= 2
            and helm_on.wall_clock_seconds <= baseline.wall_clock_seconds * 1.10
        )
        verdict_lines.append(
            "Independent suite: PASS"
            if passed
            else "Independent suite: FAIL (expect ≤2 Helm calls and <10% wall-clock overhead)"
        )
    elif baseline.suite == "conflicting":
        coord_baseline = baseline.intents_declared + baseline.conflicts_resolved
        coord_helm = helm_on.intents_declared + helm_on.conflicts_resolved
        savings = coord_baseline == 0 or coord_helm <= coord_baseline * 0.70
        fewer_conflicts = helm_on.git_conflict_files < baseline.git_conflict_files
        faster = helm_on.wall_clock_seconds < baseline.wall_clock_seconds
        passed = fewer_conflicts or faster or savings
        verdict_lines.append(
            "Conflicting suite: PASS"
            if passed
            else "Conflicting suite: FAIL (need fewer conflicts, faster merge, or ≥30% coordination savings)"
        )

    verdict = "\n".join(verdict_lines)
    md = f"# Streamcast benchmark report\n\n## Comparison ({baseline.run_id} vs {helm_on.run_id})\n\n{header}{body}\n\n## Verdict\n\n{verdict}\n"
    return md, passed


def write_comparison(
    results_dir: Path,
    baseline_run_id: str,
    helm_run_id: str,
) -> Path:
    baseline = RunReport(**json.loads((results_dir / baseline_run_id / "report.json").read_text()))
    helm_on = RunReport(**json.loads((results_dir / helm_run_id / "report.json").read_text()))
    md, _ = compare_reports(baseline, helm_on)
    out = results_dir / f"compare-{baseline_run_id}-vs-{helm_run_id}"
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "REPORT.md"
    report_path.write_text(md, encoding="utf-8")
    (out / "baseline.json").write_text(json.dumps(asdict(baseline), indent=2), encoding="utf-8")
    (out / "helm_on.json").write_text(json.dumps(asdict(helm_on), indent=2), encoding="utf-8")
    return report_path
