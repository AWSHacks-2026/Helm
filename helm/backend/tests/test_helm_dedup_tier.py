import os
from unittest.mock import patch

os.environ["HELM_MOCK_BEDROCK"] = "0"

from helm import detect_duplication


@patch("helm.invoke_anthropic_messages")
def test_pairwise_dedup_uses_haiku_for_simple_case(mock_invoke, monkeypatch):
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "0")
    from bedrock.invoke_tracked import InvokeUsage

    mock_invoke.return_value = (
        '{"duplicate_detected": false, "agent_to_continue": "agent_a", '
        '"agent_to_reassign": "agent_b", "suggested_new_task": "x", '
        '"reasoning": "ok", "tokens_saved_estimate": "~100"}',
        InvokeUsage(
            model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1,
            role="helm-dedup-haiku",
        ),
    )
    result = detect_duplication(
        agent_a={"intent": "short", "code": ""},
        agent_b={"intent": "brief", "code": ""},
    )
    assert result["inference_tier"] == "haiku"
    _, kwargs = mock_invoke.call_args
    assert "haiku" in kwargs["model_id"].lower() or "claude" in kwargs["model_id"].lower()
