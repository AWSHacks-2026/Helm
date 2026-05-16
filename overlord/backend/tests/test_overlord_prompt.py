from overlord_prompt import build_merge_conflict_prompt


def test_build_merge_conflict_prompt_includes_both_intents_and_code():
    prompt = build_merge_conflict_prompt(
        agent_a={"intent": "speed via cache", "code": "def get_user(): pass"},
        agent_b={"intent": "readability", "code": "def get_user(user_id: str): pass"},
    )
    assert "speed via cache" in prompt
    assert "readability" in prompt
    assert "def get_user(): pass" in prompt
    assert "def get_user(user_id: str): pass" in prompt
    assert "merge_conflict" in prompt
    assert "resolved_code" in prompt
