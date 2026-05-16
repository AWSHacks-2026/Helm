from bedrock import agentcore_memory as mem


def test_agents_on_file_from_local_memory(monkeypatch, tmp_path):
    monkeypatch.setenv("OVERLORD_USE_LOCAL_MEMORY", "true")
    monkeypatch.setenv("OVERLORD_SESSION_PATH", str(tmp_path / "session.json"))
    sid = "sess-multi"
    mem.log_intent(sid, "agent_a", "cache user.py", file_path="src/user.py")
    mem.log_intent(sid, "agent_b", "types on user.py", file_path="src/user.py")
    agents = mem.agents_on_file(sid, "src/user.py", exclude="agent_b")
    assert agents == ["agent_a"]
