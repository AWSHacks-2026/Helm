"""ShopFix live benchmark — delegates to live_matrix engine."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from agents.live_matrix.engine import LiveAppConfig, run_live_pair
from agents.live_matrix.engine import run_baseline_live as _engine_baseline
from agents.live_matrix.engine import run_helm_live as _engine_helm
from agents.shopfix_scenarios import FIXTURE_ROOT, SCENARIO_DIR


def resolve_fixture() -> Path:
    env = os.getenv("SHOPFIX_FIXTURE_DIR")
    if env:
        return Path(env).resolve()
    return FIXTURE_ROOT


def run_verify(repo_root: Path) -> subprocess.CompletedProcess[str]:
    backend = repo_root / "backend"
    venv_python = backend / ".venv" / "bin" / "python"
    if venv_python.exists():
        cmd = "source .venv/bin/activate && pytest -q"
    else:
        cmd = (
            "python3.11 -m venv .venv && source .venv/bin/activate && "
            "pip install -q -r requirements.txt && pytest -q"
        )
    return subprocess.run(
        ["bash", "-lc", cmd],
        cwd=backend,
        capture_output=True,
        text=True,
    )


def app_config() -> LiveAppConfig:
    return LiveAppConfig(
        app_name="shopfix",
        fixture_root=resolve_fixture(),
        scenario_dir=SCENARIO_DIR,
        session_prefix="shopfix-live",
        verify=run_verify,
    )


def run_baseline_live(suite: str, agent_count: int, work_dir: Path, **kwargs: Any) -> dict[str, Any]:
    if os.getenv("LIVE_BENCHMARK_DISABLED", "0") == "1":
        raise RuntimeError("LIVE_BENCHMARK_DISABLED=1")
    return _engine_baseline(app_config(), suite, agent_count, work_dir, **kwargs)


def run_helm_live(suite: str, agent_count: int, work_dir: Path, **kwargs: Any) -> dict[str, Any]:
    if os.getenv("LIVE_BENCHMARK_DISABLED", "0") == "1":
        raise RuntimeError("LIVE_BENCHMARK_DISABLED=1")
    return _engine_helm(app_config(), suite, agent_count, work_dir, **kwargs)


def run_shopfix_live_pair(suite: str, agent_count: int, work_dir: Path) -> dict[str, Any]:
    if os.getenv("LIVE_BENCHMARK_DISABLED", "0") == "1":
        raise RuntimeError("LIVE_BENCHMARK_DISABLED=1")
    return run_live_pair(app_config(), suite, agent_count, work_dir)


def format_summary(result: dict[str, Any]) -> str:
    c = result["comparison"]
    lines = [
        f"ShopFix LIVE — {result['suite']} — N={result['agent_count']}",
        f"  mock_bedrock={result['mock_bedrock']}",
        f"  baseline: {c['baseline_cost_display']} / {c['baseline_seconds']}s "
        f"sonnet={c.get('baseline_sonnet_calls', 0)} tests={c['baseline_tests_pass']}",
        f"  helm:     {c['helm_cost_display']} / {c['helm_seconds']}s "
        f"sonnet={c.get('helm_sonnet_calls', 0)} dedup={c.get('helm_dedup_calls', 0)} "
        f"gate_skipped={c.get('helm_gate_skipped')} tests={c['helm_tests_pass']}",
        f"  savings:  {c['cost_savings_pct']}% cost, {c['time_savings_pct']}% time",
    ]
    return "\n".join(lines)
