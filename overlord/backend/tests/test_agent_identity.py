import os
from session.agent_identity import resolve_agent_id


def test_resolve_agent_id_from_env(monkeypatch):
    monkeypatch.setenv("OVERLORD_AGENT_ID", "agent_a")
    assert resolve_agent_id() == "agent_a"


def test_resolve_agent_id_default(monkeypatch):
    monkeypatch.delenv("OVERLORD_AGENT_ID", raising=False)
    assert resolve_agent_id() == "agent_local"
