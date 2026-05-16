from overlord_prompt import (
    build_guardrail_resolution_prompt,
    build_intent_conflict_prompt,
)


def test_build_intent_conflict_prompt_mentions_both_intents():
    prompt = build_intent_conflict_prompt(
        agent_a={"intent": "max performance", "code": "# a"},
        agent_b={"intent": "min dependencies", "code": "# b"},
    )
    assert "max performance" in prompt
    assert "min dependencies" in prompt
    assert "intent_conflict" in prompt


def test_build_guardrail_resolution_prompt_mentions_block():
    prompt = build_guardrail_resolution_prompt(
        agent_a={"intent": "keep cache", "code": "# keep"},
        agent_b={"intent": "delete cache", "code": "# delete"},
        proposed_action={"description": "Remove caching utility"},
        rule="reverses_recent_decision",
        message="Blocked delete",
    )
    assert "reverses_recent_decision" in prompt
    assert "Remove caching utility" in prompt
