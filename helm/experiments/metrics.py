"""Aggregate metrics for multi-agent experiment runs (no Helm)."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentRunResult:
    agent_id: str
    file_path: str
    code: str
    elapsed_ms: int
    input_tokens: int
    output_tokens: int
    syntax_ok: bool


@dataclass
class ThemeRunResult:
    theme_name: str
    assignments: list[dict[str, Any]]
    agent_runs: list[AgentRunResult] = field(default_factory=list)
    base_files: dict[str, str] = field(default_factory=dict)


def _normalize(code: str) -> str:
    return "\n".join(line.rstrip() for line in code.strip().splitlines())


def count_conflict_edits(runs: list[AgentRunResult]) -> int:
    """Files touched by 2+ agents with different normalized content."""
    by_file: dict[str, list[str]] = {}
    for run in runs:
        by_file.setdefault(run.file_path, []).append(_normalize(run.code))
    conflicts = 0
    for path, versions in by_file.items():
        if len(versions) < 2:
            continue
        unique = {v for v in versions}
        if len(unique) > 1:
            conflicts += 1
    return conflicts


def count_reverted_commits(
    base_files: dict[str, str],
    runs: list[AgentRunResult],
) -> int:
    """
    Sequential apply: agent_alpha then agent_beta per file.
    Count files where beta output does not contain alpha content (rough revert).
    """
    by_path: dict[str, dict[str, str]] = {}
    for run in runs:
        by_path.setdefault(run.file_path, {})[run.agent_id] = run.code

    reverts = 0
    paths = set(base_files) | set(by_path)
    for path in paths:
        agents = by_path.get(path, {})
        alpha = agents.get("agent_alpha", "")
        beta = agents.get("agent_beta", "")
        if not alpha or not beta:
            continue
        na = _normalize(alpha)
        nb = _normalize(beta)
        if na == nb:
            continue
        if len(na) > 20 and na not in nb:
            reverts += 1
    return reverts


def apply_agent_code(base_files: dict[str, str], code: str) -> dict[str, str]:
    merged = dict(base_files)
    merged[code] = code  # single-file agent for simplicity in metrics
    return merged


def sequential_merge_build_ok(
    base_files: dict[str, str],
    runs: list[AgentRunResult],
) -> tuple[int, int]:
    """Returns (files_parsed_ok, total_files)."""
    state = dict(base_files)
    order = sorted({r.agent_id for r in runs})
    for aid in order:
        for run in runs:
            if run.agent_id not in order:
                continue
            if run.file_path in state:
                state[run.file_path] = run.code
            else:
                state[run.file_path] = run.code
    parsed = 0
    for path, content in state.items():
        try:
            ast.parse(content)
            parsed += 1
        except SyntaxError:
            pass
    return parsed, len(state)


def total_tokens(runs: list[AgentRunResult]) -> int:
    return sum(r.input_tokens + r.output_tokens for r in runs)


def total_resolution_ms(runs: list[AgentRunResult]) -> int:
    return sum(r.elapsed_ms for r in runs)


def agent_success_rate(runs: list[AgentRunResult]) -> float:
    if not runs:
        return 0.0
    return sum(1 for r in runs if r.syntax_ok) / len(runs)


def merge_success_rate(
    base_files: dict[str, str],
    runs: list[AgentRunResult],
) -> float:
    if not base_files:
        return 0.0
    parsed, total = sequential_merge_build_ok(base_files, runs)
    return parsed / total if total else 0.0


def summarize_run(result: ThemeRunResult) -> dict[str, Any]:
    runs = result.agent_runs
    return {
        "theme": result.theme_name,
        "conflict_edits": count_conflict_edits(runs),
        "reverted_commits": count_reverted_commits(result.base_files, runs),
        "total_tokens": total_tokens(runs),
        "resolution_time_ms": total_resolution_ms(runs),
        "agent_success_rate": round(agent_success_rate(runs), 4),
        "successful_build_rate": round(merge_success_rate(result.base_files, runs), 4),
        "merge_success_rate": round(merge_success_rate(result.base_files, runs), 4),
        "agents": {
            aid: {
                "runs": len([r for r in runs if r.agent_id == aid]),
                "tokens": sum(r.input_tokens + r.output_tokens for r in runs if r.agent_id == aid),
                "success_rate": round(
                    sum(1 for r in runs if r.agent_id == aid and r.syntax_ok)
                    / max(1, len([r for r in runs if r.agent_id == aid])),
                    4,
                ),
            }
            for aid in sorted({r.agent_id for r in runs})
        },
    }
