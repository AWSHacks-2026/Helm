import json
from unittest.mock import MagicMock, patch

import pytest

from overlord import OVERLORD_MODEL, detect_duplication


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
    monkeypatch.setenv("OVERLORD_MOCK_BEDROCK", "1")
    agent_a, agent_b = _agents()

    result = detect_duplication(
        agent_a=agent_a,
        agent_b=agent_b,
    )

    assert result == {
        "conflict_type": "duplicate_work",
        "duplicate_detected": True,
        "agent_to_continue": "agent_a",
        "agent_to_reassign": "agent_b",
        "suggested_new_task": "Implement audit logging for authentication events.",
        "reasoning": (
            "Both agents are working on overlapping user authentication tasks; "
            "Agent A should continue because its scope covers the login flow, while "
            "Agent B should move to adjacent audit logging work."
        ),
        "resolved_code": "",
        "tokens_saved_estimate": "~1800 (mock)",
    }


@patch("overlord.get_bedrock_client")
def test_detect_duplication_calls_sonnet_and_parses_json(mock_get_client, monkeypatch):
    monkeypatch.delenv("OVERLORD_MOCK_BEDROCK", raising=False)
    mock_client = _configure_bedrock_response(
        mock_get_client,
        {
            "conflict_type": "duplicate_work",
            "duplicate_detected": True,
            "agent_to_continue": "agent_a",
            "agent_to_reassign": "agent_b",
            "suggested_new_task": "Implement password reset email templates.",
            "reasoning": "Both intents target authentication; split off password reset work.",
        },
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

    mock_client.invoke_model.assert_called_once()
    call_kwargs = mock_client.invoke_model.call_args.kwargs
    assert call_kwargs["modelId"] == OVERLORD_MODEL
    body = json.loads(call_kwargs["body"])
    assert body["anthropic_version"] == "bedrock-2023-05-31"
    assert body["max_tokens"] == 1000
    assert "duplicate_detected" in body["messages"][0]["content"]


@patch("overlord.get_bedrock_client")
def test_detect_duplication_rejects_non_boolean_duplicate_detected(
    mock_get_client, monkeypatch
):
    monkeypatch.delenv("OVERLORD_MOCK_BEDROCK", raising=False)
    _configure_bedrock_response(
        mock_get_client,
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


@patch("overlord.get_bedrock_client")
def test_detect_duplication_rejects_invalid_agent_assignment(
    mock_get_client, monkeypatch
):
    monkeypatch.delenv("OVERLORD_MOCK_BEDROCK", raising=False)
    _configure_bedrock_response(
        mock_get_client,
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


@patch("overlord.get_bedrock_client")
def test_detect_duplication_rejects_same_agent_assignment(mock_get_client, monkeypatch):
    monkeypatch.delenv("OVERLORD_MOCK_BEDROCK", raising=False)
    _configure_bedrock_response(
        mock_get_client,
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
