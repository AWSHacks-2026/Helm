"""Streamcast live benchmark — delegates to live_matrix engine."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from agents.live_matrix.engine import LiveAppConfig, run_baseline_live, run_helm_live, run_live_pair
from agents.streamcast_scenarios import FIXTURE_ROOT, SCENARIO_DIR


def resolve_fixture() -> Path:
    env = os.getenv("STREAMCAST_FIXTURE_DIR")
    if env:
        return Path(env).resolve()
    return FIXTURE_ROOT


def run_verify(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )


def app_config() -> LiveAppConfig:
    return LiveAppConfig(
        app_name="streamcast",
        fixture_root=resolve_fixture(),
        scenario_dir=SCENARIO_DIR,
        session_prefix="streamcast-live",
        verify=run_verify,
    )


def run_streamcast_live_pair(suite: str, agent_count: int, work_dir: Path, **kwargs):
    return run_live_pair(app_config(), suite, agent_count, work_dir, **kwargs)


def run_baseline(suite: str, agent_count: int, work_dir: Path, **kwargs):
    return run_baseline_live(app_config(), suite, agent_count, work_dir, **kwargs)


def run_helm(suite: str, agent_count: int, work_dir: Path, **kwargs):
    return run_helm_live(app_config(), suite, agent_count, work_dir, **kwargs)
