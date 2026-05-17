from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

SuiteName = Literal["independent", "conflicting"]


@dataclass(frozen=True)
class Assignment:
    id: str
    branch: str
    feature: str
    files: list[str]


@dataclass(frozen=True)
class SuiteManifest:
    suite: SuiteName
    session_id_prefix: str
    repo_subdir: str
    assignments: list[Assignment]


def load_suite_manifest(path: Path) -> SuiteManifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    suite = raw.get("suite", "")
    if suite not in ("independent", "conflicting"):
        raise ValueError(f"invalid suite: {suite}")
    assignments = [
        Assignment(
            id=item["id"],
            branch=item["branch"],
            feature=item["feature"],
            files=list(item["files"]),
        )
        for item in raw.get("assignments", [])
    ]
    if not assignments:
        raise ValueError("manifest must define at least one assignment")
    if suite == "independent":
        flat = [f for a in assignments for f in a.files]
        if len(flat) != len(set(flat)):
            raise ValueError("independent suite assignments must be file-disjoint")
    manifest = SuiteManifest(
        suite=suite,
        session_id_prefix=raw.get("session_id_prefix", f"streamcast-{suite}"),
        repo_subdir=raw.get("repo_subdir", "streamcast"),
        assignments=assignments,
    )
    return manifest
