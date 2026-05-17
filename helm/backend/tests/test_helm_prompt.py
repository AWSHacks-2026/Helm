from helm_prompt import build_merge_conflict_prompt, build_task_deduplication_prompt


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


def test_build_task_deduplication_prompt_requests_required_json_fields():
    prompt = build_task_deduplication_prompt(
        agent_a={
            "intent": "I am implementing JWT-based user authentication.",
            "code": "# login",
            "proposed_action": "Build auth login endpoints.",
        },
        agent_b={
            "intent": "I am building sign-in and session validation.",
            "code": "# sign-in",
            "proposed_action": "Build sign-in checks.",
        },
    )

    assert "semantic task deduplication" in prompt.lower()
    assert "duplicate_detected" in prompt
    assert "agent_to_continue" in prompt
    assert "agent_to_reassign" in prompt
    assert "suggested_new_task" in prompt
    assert "reasoning" in prompt
    assert "JWT-based user authentication" in prompt
    assert "sign-in and session validation" in prompt
