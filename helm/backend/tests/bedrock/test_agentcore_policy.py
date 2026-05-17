from bedrock import agentcore_memory as mem
from bedrock.agentcore_policy import evaluate_proposed_action


def test_local_policy_blocks_delete_after_peer_add():
    mem.log_action("s1", "agent_a", "add_file", "utils/cache.py", "Added cache")
    result = evaluate_proposed_action(
        session_id="s1",
        proposed_action={
            "agent_id": "agent_b",
            "action_type": "delete_file",
            "file_path": "utils/cache.py",
            "description": "Remove cache",
        },
    )
    assert result.allowed is False
    assert result.rule == "reverses_recent_decision"


def test_local_policy_allows_unrelated_write():
    result = evaluate_proposed_action(
        session_id="s2",
        proposed_action={
            "agent_id": "agent_b",
            "action_type": "modify_file",
            "file_path": "other.py",
            "description": "Refactor",
        },
    )
    assert result.allowed is True
