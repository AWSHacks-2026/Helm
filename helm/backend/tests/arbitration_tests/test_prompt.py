from arbitration.prompt import build_merge_conflict_prompt


def test_build_merge_conflict_prompt_includes_both_agents():
    prompt = build_merge_conflict_prompt(
        agent_a={"intent": "add caching", "code": "def get_user(user_id): ..."},
        agent_b={"intent": "add types", "code": "def get_user(user_id: str) -> User: ..."},
    )
    assert "add caching" in prompt
    assert "add types" in prompt
    assert "merge_conflict" in prompt
    assert "Agent A code:" in prompt
    assert "Agent B code:" in prompt
