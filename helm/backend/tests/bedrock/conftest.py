import os

import pytest


@pytest.fixture(autouse=True)
def isolated_agentcore_env(tmp_path, monkeypatch):
    session_file = tmp_path / "session.json"
    monkeypatch.setenv("HELM_USE_LOCAL_MEMORY", "true")
    monkeypatch.setenv("HELM_USE_LOCAL_POLICY", "true")
    monkeypatch.setenv("HELM_USE_LOCAL_KB", "true")
    monkeypatch.setenv("HELM_SESSION_PATH", str(session_file))
    monkeypatch.delenv("AGENTCORE_MEMORY_ID", raising=False)
    monkeypatch.delenv("AGENTCORE_POLICY_ENGINE_ID", raising=False)
    monkeypatch.delenv("BEDROCK_KB_ID", raising=False)
    monkeypatch.delenv("BEDROCK_GUARDRAIL_ID", raising=False)
    yield session_file
