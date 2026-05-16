import os
from pathlib import Path
import pytest

@pytest.fixture(autouse=True)
def isolated_kb_session(tmp_path, monkeypatch):
    session_file = tmp_path / "session.json"
    monkeypatch.setenv("OVERLORD_USE_LOCAL_KB", "true")
    monkeypatch.setenv("OVERLORD_SESSION_PATH", str(session_file))
    monkeypatch.delenv("BEDROCK_KB_ID", raising=False)
    monkeypatch.delenv("BEDROCK_GUARDRAIL_ID", raising=False)
    yield session_file
