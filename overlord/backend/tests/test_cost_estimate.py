from bedrock.cost_estimate import (
    build_cost_comparison,
    estimate_usd,
    format_usd,
    model_tier,
)


def test_model_tier():
    assert model_tier("us.anthropic.claude-haiku-4-5-20251001-v1:0") == "haiku"
    assert model_tier("us.anthropic.claude-sonnet-4-6") == "sonnet"


def test_sonnet_costs_more_than_haiku_for_same_tokens():
    haiku = estimate_usd("haiku", 1000, 1000)
    sonnet = estimate_usd("sonnet", 1000, 1000)
    assert sonnet > haiku


def test_build_cost_comparison():
    baseline = {
        "calls": [
            {
                "model_id": "us.anthropic.claude-haiku-4-5",
                "input_tokens": 10_000,
                "output_tokens": 2_000,
            }
        ]
    }
    overlord = {
        "calls": [
            {
                "model_id": "us.anthropic.claude-sonnet-4-6",
                "input_tokens": 2_000,
                "output_tokens": 1_000,
            },
            {
                "model_id": "us.anthropic.claude-haiku-4-5",
                "input_tokens": 3_000,
                "output_tokens": 500,
            },
        ]
    }
    c = build_cost_comparison(baseline, overlord)
    assert c["baseline_cost_usd"] > 0
    assert c["overlord_cost_usd"] > 0
    assert "baseline_cost_display" in c
    assert format_usd(0.001) == "$0.0010"
