import subprocess
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


def test_commit_staged_after_resolving_two_merge_conflicts(tmp_path):
    """Per-file commits fail with exit 128 while other paths stay unmerged."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    (repo / "a.txt").write_text("base\n")
    (repo / "b.txt").write_text("base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=T", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "branch", "feature"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "feature"], cwd=repo, check=True, capture_output=True)
    (repo / "a.txt").write_text("feature a\n")
    (repo / "b.txt").write_text("feature b\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=T", "commit", "-m", "feature"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True, capture_output=True)
    (repo / "a.txt").write_text("main a\n")
    (repo / "b.txt").write_text("main b\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=T", "commit", "-m", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    proc = subprocess.run(
        ["git", "merge", "--no-edit", "feature"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0

    sandbox = GitSandbox(root=repo)
    assert sandbox.merge_in_progress()
    assert len(sandbox.conflicted_paths()) == 2

    sandbox.stage_file("a.txt", "merged a\n")
    with pytest.raises(subprocess.CalledProcessError):
        sandbox._run(
            "git",
            "-c",
            "user.email=helm@shopfix.test",
            "-c",
            "user.name=Helm",
            "commit",
            "-m",
            "resolve a only",
        )

    sandbox.stage_file("b.txt", "merged b\n")
    assert sandbox.commit_staged("resolve merge conflicts")
    assert sandbox.conflicted_paths() == []
    assert not sandbox.merge_in_progress()
