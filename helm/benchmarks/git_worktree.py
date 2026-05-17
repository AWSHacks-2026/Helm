from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from benchmarks.manifest import Assignment


@dataclass
class MergeResult:
    success: bool
    conflict_files: list[str]
    merge_commit: str | None


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def prepare_run(repo_root: Path, run_id: str, base_branch: str = "streamcast-base") -> Path:
    """Initialize git repo layout and return worktrees root for a benchmark run."""
    repo_root.mkdir(parents=True, exist_ok=True)
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        _run(["git", "init"], cwd=repo_root)
        _run(["git", "config", "user.email", "benchmark@helm.local"], cwd=repo_root)
        _run(["git", "config", "user.name", "Helm Benchmark"], cwd=repo_root)
    _run(["git", "add", "-A"], cwd=repo_root)
    status = _run(["git", "status", "--porcelain"], cwd=repo_root, check=False)
    if status.stdout.strip():
        _run(["git", "commit", "-m", "chore(benchmark): streamcast baseline"], cwd=repo_root)
    branches = _run(["git", "branch", "--list", base_branch], cwd=repo_root, check=False)
    if base_branch not in branches.stdout:
        _run(["git", "branch", base_branch], cwd=repo_root)
    worktrees_root = repo_root / ".benchmark-worktrees" / run_id
    worktrees_root.mkdir(parents=True, exist_ok=True)
    return worktrees_root


def create_agent_worktree(worktrees_root: Path, assignment: Assignment, base_branch: str = "streamcast-base") -> Path:
    """Create an isolated worktree branch for one agent assignment."""
    repo_root = worktrees_root.parent.parent
    agent_dir = worktrees_root / assignment.id
    if agent_dir.exists():
        return agent_dir
    agent_dir.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "git",
            "worktree",
            "add",
            "-B",
            assignment.branch,
            str(agent_dir),
            base_branch,
        ],
        cwd=repo_root,
    )
    return agent_dir


def commit_all(agent_dir: Path, message: str) -> str:
    """Stage and commit all changes in an agent worktree."""
    _run(["git", "add", "-A"], cwd=agent_dir)
    status = _run(["git", "status", "--porcelain"], cwd=agent_dir, check=False)
    if not status.stdout.strip():
        sha = _run(["git", "rev-parse", "HEAD"], cwd=agent_dir).stdout.strip()
        return sha
    _run(["git", "commit", "-m", message], cwd=agent_dir)
    return _run(["git", "rev-parse", "HEAD"], cwd=agent_dir).stdout.strip()


def _conflict_files(repo_root: Path) -> list[str]:
    result = _run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=repo_root,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def merge_branches(
    worktrees_root: Path,
    branches: list[str],
    target: str = "integration",
) -> MergeResult:
    """Merge agent branches sequentially into target branch inside the bare repo root."""
    repo_root = worktrees_root.parent.parent
    _run(["git", "checkout", "-B", target, "streamcast-base"], cwd=repo_root)
    merge_commit: str | None = None
    conflict_files: list[str] = []
    for branch in branches:
        result = _run(
            ["git", "merge", "--no-edit", branch],
            cwd=repo_root,
            check=False,
        )
        if result.returncode != 0:
            conflict_files = _conflict_files(repo_root)
            _run(["git", "merge", "--abort"], cwd=repo_root, check=False)
            return MergeResult(success=False, conflict_files=conflict_files, merge_commit=None)
        merge_commit = _run(["git", "rev-parse", "HEAD"], cwd=repo_root).stdout.strip()
    return MergeResult(success=True, conflict_files=[], merge_commit=merge_commit)
