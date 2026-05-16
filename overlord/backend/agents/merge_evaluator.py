from __future__ import annotations

import ast
from typing import Any


def _normalize(code: str) -> str:
    return "\n".join(line.rstrip() for line in code.strip().splitlines())


def _syntax_ok(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def evaluate_merge_resolution(
    resolved_code: str,
    agent_a_code: str,
    agent_b_code: str,
    acceptance: dict[str, Any],
) -> dict[str, Any]:
    """Score a merge resolution against heuristic acceptance criteria."""
    code = resolved_code or ""
    lower = code.lower()
    checks: dict[str, bool] = {}

    checks["non_empty"] = bool(code.strip())
    checks["syntax_valid"] = _syntax_ok(code) if checks["non_empty"] else False

    for token in acceptance.get("must_include", []):
        checks[f"includes_{token}"] = token.lower() in lower

    for group in acceptance.get("must_include_any", []):
        key = "any_" + "_".join(group[:2])[:40]
        checks[key] = any(t.lower() in lower for t in group)

    if acceptance.get("must_not_equal_agent"):
        norm = _normalize(code)
        checks["not_only_agent_a"] = norm != _normalize(agent_a_code)
        checks["not_only_agent_b"] = norm != _normalize(agent_b_code)

    passed = all(checks.values())
    score = int(100 * sum(checks.values()) / len(checks)) if checks else 0

    return {
        "passed": passed,
        "score": score,
        "checks": checks,
    }
