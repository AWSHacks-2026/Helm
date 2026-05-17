from bedrock.inference_routing import (
    ComplexityInput,
    compute_complexity_score,
    select_inference_tier,
)


def test_simple_dedup_pairwise_prefers_haiku():
    inp = ComplexityInput(
        operation="dedup",
        agent_count=2,
        file_count=1,
        kb_event_count=0,
        total_text_chars=200,
        preflight_rule=None,
        has_substantive_code=False,
    )
    assert select_inference_tier(inp) == "haiku"
    assert compute_complexity_score(inp) < 50


def test_fleet_dedup_prefers_sonnet():
    inp = ComplexityInput(
        operation="dedup",
        agent_count=4,
        file_count=2,
        kb_event_count=10,
        total_text_chars=4000,
        preflight_rule=None,
        has_substantive_code=False,
    )
    assert select_inference_tier(inp) == "sonnet"
