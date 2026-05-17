from pathlib import Path

from benchmarks.git_worktree import (
    commit_all,
    create_agent_worktree,
    merge_branches,
    prepare_run,
)
from benchmarks.manifest import Assignment


def test_merge_detects_conflicts(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "shared.txt").write_text("base\n", encoding="utf-8")

    run_id = "test-run"
    worktrees_root = prepare_run(repo, run_id)
    assignment_a = Assignment(
        id="agent_a",
        branch="agent/a",
        feature="edit shared",
        files=["shared.txt"],
    )
    assignment_b = Assignment(
        id="agent_b",
        branch="agent/b",
        feature="edit shared",
        files=["shared.txt"],
    )

    dir_a = create_agent_worktree(worktrees_root, assignment_a)
    dir_b = create_agent_worktree(worktrees_root, assignment_b)

    (dir_a / "shared.txt").write_text("line from A\n", encoding="utf-8")
    (dir_b / "shared.txt").write_text("line from B\n", encoding="utf-8")
    commit_all(dir_a, "feat(agent_a): change A")
    commit_all(dir_b, "feat(agent_b): change B")

    result = merge_branches(worktrees_root, [assignment_a.branch, assignment_b.branch])
    assert result.success is False
    assert result.conflict_files
