import json
from unittest.mock import MagicMock, patch

import pytest

from helm import HELM_MODEL, detect_duplication


def _bedrock_body(text: str) -> dict:
    return {
        "content": [{"type": "text", "text": text}],
    }


def _agents() -> tuple[dict, dict]:
    return (
        {
            "intent": "I am implementing JWT-based user authentication.",
            "code": "# login",
            "proposed_action": "Build login endpoints.",
        },
        {
            "intent": "I am building sign-in and session validation.",
            "code": "# sign-in",
            "proposed_action": "Build sign-in checks.",
        },
    )


def _configure_bedrock_response(mock_get_client, model_payload: dict) -> MagicMock:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    model_json = json.dumps(model_payload)
    mock_client.invoke_model.return_value = {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps(_bedrock_body(model_json)).encode()
            )
        )
    }
    return mock_client


def test_detect_duplication_returns_mock_result_when_enabled(monkeypatch):
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "1")
    agent_a, agent_b = _agents()

    result = detect_duplication(
        agent_a=agent_a,
        agent_b=agent_b,
    )

    assert result["conflict_type"] == "duplicate_work"
    assert result["duplicate_detected"] is True
    assert result["agent_to_continue"] == "agent_a"
    assert result["agent_to_reassign"] == "agent_b"
    assert result["inference_tier"] == "haiku"


@patch("helm.invoke_anthropic_messages")
def test_detect_duplication_calls_sonnet_and_parses_json(mock_invoke, monkeypatch):
    from bedrock.invoke_tracked import InvokeUsage

    monkeypatch.delenv("HELM_MOCK_BEDROCK", raising=False)
    model_json = json.dumps(
        {
            "conflict_type": "duplicate_work",
            "duplicate_detected": True,
            "agent_to_continue": "agent_a",
            "agent_to_reassign": "agent_b",
            "suggested_new_task": "Implement password reset email templates.",
            "reasoning": "Both intents target authentication; split off password reset work.",
        }
    )
    mock_invoke.return_value = (
        model_json,
        InvokeUsage(HELM_MODEL, "helm-dedup", 100, 50, 10),
    )
    agent_a, agent_b = _agents()

    result = detect_duplication(
        agent_a=agent_a,
        agent_b=agent_b,
    )

    assert result["duplicate_detected"] is True
    assert result["agent_to_continue"] == "agent_a"
    assert result["agent_to_reassign"] == "agent_b"
    assert result["suggested_new_task"] == "Implement password reset email templates."
    assert result["resolved_code"] == ""
    assert result["tokens_saved_estimate"] == "~1800"
    assert result["_usage"]["input_tokens"] == 100

    mock_invoke.assert_called_once()
    assert result["inference_tier"] in {"haiku", "sonnet"}
    model_id = mock_invoke.call_args.kwargs["model_id"]
    assert model_id
    prompt = mock_invoke.call_args.kwargs["messages"][0]["content"]
    assert "duplicate_detected" in prompt


def _mock_invoke_return(payload: dict) -> tuple[str, object]:
    from bedrock.invoke_tracked import InvokeUsage

    return json.dumps(payload), InvokeUsage(HELM_MODEL, "helm-dedup", 10, 5, 1)


@patch("helm.invoke_anthropic_messages")
def test_detect_duplication_rejects_non_boolean_duplicate_detected(
    mock_invoke, monkeypatch
):
    monkeypatch.delenv("HELM_MOCK_BEDROCK", raising=False)
    mock_invoke.return_value = _mock_invoke_return(
        {
            "conflict_type": "duplicate_work",
            "duplicate_detected": "false",
            "agent_to_continue": "agent_a",
            "agent_to_reassign": "agent_b",
            "suggested_new_task": "Implement password reset email templates.",
            "reasoning": "Both intents target authentication; split off password reset work.",
        },
    )
    agent_a, agent_b = _agents()

    with pytest.raises(ValueError, match="duplicate_detected must be a boolean"):
        detect_duplication(agent_a=agent_a, agent_b=agent_b)


@patch("helm.invoke_anthropic_messages")
def test_detect_duplication_rejects_invalid_agent_assignment(
    mock_invoke, monkeypatch
):
    monkeypatch.delenv("HELM_MOCK_BEDROCK", raising=False)
    mock_invoke.return_value = _mock_invoke_return(
        {
            "conflict_type": "duplicate_work",
            "duplicate_detected": True,
            "agent_to_continue": "agent_c",
            "agent_to_reassign": "agent_b",
            "suggested_new_task": "Implement password reset email templates.",
            "reasoning": "Both intents target authentication; split off password reset work.",
        },
    )
    agent_a, agent_b = _agents()

    with pytest.raises(ValueError, match="agent assignments must be agent_a or agent_b"):
        detect_duplication(agent_a=agent_a, agent_b=agent_b)


@patch("helm.invoke_anthropic_messages")
def test_detect_duplication_rejects_same_agent_assignment(mock_invoke, monkeypatch):
    monkeypatch.delenv("HELM_MOCK_BEDROCK", raising=False)
    mock_invoke.return_value = _mock_invoke_return(
        {
            "conflict_type": "duplicate_work",
            "duplicate_detected": True,
            "agent_to_continue": "agent_a",
            "agent_to_reassign": "agent_a",
            "suggested_new_task": "Implement password reset email templates.",
            "reasoning": "Both intents target authentication; split off password reset work.",
        },
    )
    agent_a, agent_b = _agents()

    with pytest.raises(
        ValueError, match="agent_to_continue and agent_to_reassign must differ"
    ):
        detect_duplication(agent_a=agent_a, agent_b=agent_b)
