from unittest.mock import MagicMock

from bedrock.guardrails import check_action


def test_check_action_uses_memory_when_cloud(monkeypatch, tmp_path):
    monkeypatch.setenv("OVERLORD_USE_LOCAL_MEMORY", "true")
    monkeypatch.setenv("OVERLORD_SESSION_PATH", str(tmp_path / "session.json"))
    from bedrock import agentcore_memory as mem

    sid = "shared-sess"
    mem.log_intent(sid, "agent_a", "work on file", file_path="f.py")
    store = MagicMock()
    store.agents_on_file.return_value = []

    result = check_action(
        session_id=sid,
        agent_id="agent_b",
        file_path="f.py",
        action="write",
        proposed_code="x",
        session_store=store,
    )
    assert result.allowed is False
    assert "agent_a" in result.reason
