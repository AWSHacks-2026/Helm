from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GitSandbox:
    root: Path

    @classmethod
    def create(cls, fixture_dir: Path, work_dir: Path) -> GitSandbox:
        if work_dir.exists():
            shutil.rmtree(work_dir)
        shutil.copytree(
            fixture_dir,
            work_dir,
            ignore=shutil.ignore_patterns(
                ".git",
                "node_modules",
                ".venv",
                "dist",
                "*.db",
                "__pycache__",
                "package-lock.json",
            ),
        )
        sandbox = cls(root=work_dir)
        sandbox._run("git", "init", "-b", "main")
        sandbox._run("git", "add", ".")
        sandbox._run(
            "git",
            "-c",
            "user.email=helm@shopfix.test",
            "-c",
            "user.name=Helm",
            "commit",
            "-m",
            "baseline",
        )
        return sandbox

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args, cwd=self.root, check=check, capture_output=True, text=True
        )

    def current_branch(self) -> str:
        return self._run("git", "branch", "--show-current").stdout.strip()

    def create_branch(self, name: str) -> None:
        self._run("git", "branch", name)

    def checkout(self, name: str) -> None:
        self._run("git", "checkout", name)

    def apply_patch(self, patch_path: Path) -> None:
        self._run("git", "apply", str(patch_path))

    def commit_all(self, message: str) -> str:
        self._run("git", "add", "-A")
        self._run(
            "git",
            "-c",
            "user.email=agent@shopfix.test",
            "-c",
            "user.name=Agent",
            "commit",
            "-m",
            message,
        )
        return self._run("git", "rev-parse", "HEAD").stdout.strip()

    def merge(self, branch: str) -> bool:
        proc = subprocess.run(
            ["git", "merge", "--no-edit", branch],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0

    def has_conflict_markers(self) -> bool:
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".tsx", ".ts", ".css"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "<<<<<<<" in text:
                return True
        return False
