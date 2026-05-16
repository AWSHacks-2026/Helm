from bedrock import agentcore_memory as mem


def test_log_action_and_list_events_local():
    mem.log_action(
        session_id="sess-1",
        actor_id="agent_a",
        action_type="add_file",
        file_path="utils/cache.py",
        description="Added cache",
    )
    events = mem.list_events(session_id="sess-1", limit=10)
    assert len(events) >= 1
    assert events[-1]["payload"]["file_path"] == "utils/cache.py"


def test_retrieve_memories_local_returns_match():
    mem.log_action("sess-2", "agent_a", "modify_file", "utils/cache.py", "cache work")
    hits = mem.retrieve_context(session_id="sess-2", query="cache utility", top_k=3)
    assert len(hits) >= 1
