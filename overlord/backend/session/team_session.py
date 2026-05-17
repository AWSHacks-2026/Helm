from __future__ import annotations

import os
import re


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def resolve_team_session_id() -> str:
    explicit = os.getenv("OVERLORD_TEAM_SESSION", "").strip()
    if explicit:
        return explicit
    repo = os.getenv("OVERLORD_REPO_SLUG", "mergeai/default")
    branch = os.getenv("OVERLORD_BRANCH", "main")
    return f"mergeai/{_slug(repo)}/{_slug(branch)}"
