from __future__ import annotations

from pathlib import Path

from agents.git_sandbox import GitSandbox


def apply_agent_patch(sandbox: GitSandbox, patch_path: Path) -> None:
    if not patch_path.exists():
        raise FileNotFoundError(patch_path)
    sandbox.apply_patch(patch_path)
    sandbox.commit_all(patch_path.stem)
