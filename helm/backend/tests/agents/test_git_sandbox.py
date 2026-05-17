from pathlib import Path

import pytest

from agents.git_sandbox import GitSandbox
from agents.shopfix_scenarios import FIXTURE_ROOT


@pytest.fixture
def fixture_dir():
    if not FIXTURE_ROOT.exists():
        pytest.skip("shopfix fixture not present")
    return FIXTURE_ROOT


def test_sandbox_creates_repo_with_main(fixture_dir, tmp_path):
    sandbox = GitSandbox.create(fixture_dir=fixture_dir, work_dir=tmp_path / "repo")
    assert (sandbox.root / ".git").exists()
    assert sandbox.current_branch() == "main"
    sandbox.create_branch("agent/agent_a")
    sandbox.checkout("agent/agent_a")
    assert sandbox.current_branch() == "agent/agent_a"
