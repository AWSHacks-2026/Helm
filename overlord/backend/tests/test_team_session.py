import os

from session.team_session import resolve_team_session_id


def test_resolve_prefers_env_override(monkeypatch):
    monkeypatch.setenv("OVERLORD_TEAM_SESSION", "team-fixed")
    assert resolve_team_session_id() == "team-fixed"


def test_resolve_builds_from_repo_slug(monkeypatch):
    monkeypatch.delenv("OVERLORD_TEAM_SESSION", raising=False)
    monkeypatch.setenv("OVERLORD_REPO_SLUG", "AWSHacks-2026/MergeAI")
    monkeypatch.setenv("OVERLORD_BRANCH", "main")
    sid = resolve_team_session_id()
    assert sid == "mergeai/awshacks-2026-mergeai/main"
