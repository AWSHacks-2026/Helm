import json
from unittest.mock import MagicMock, patch

from bedrock.invoke_tracked import InvokeUsage
from helm import HELM_MODEL, arbitrate


def _usage() -> InvokeUsage:
    return InvokeUsage("m", "helm", 10, 5, 1)


@patch("arbitration.runner.get_bedrock_client")
def test_arbitrate_returns_parsed_resolution_legacy_path(mock_get_client, monkeypatch):
    monkeypatch.delenv("HELM_MOCK_BEDROCK", raising=False)
    monkeypatch.delenv("HELM_ARBITRATOR_ARN", raising=False)

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    model_json = json.dumps(
        {
            "conflict_type": "merge_conflict",
            "reasoning": "Kept cache and type hints.",
            "resolved_code": "def get_user(user_id: str) -> User:\n    ...",
            "tokens_saved_estimate": "~2400",
        }
    )
    mock_client.invoke_model.return_value = {
        "body": MagicMock(read=lambda: json.dumps({"content": [{"text": model_json}]}).encode())
    }

    result = arbitrate(
        agent_a={"intent": "cache", "code": "def get_user(user_id): ..."},
        agent_b={"intent": "types", "code": "def get_user(user_id: str) -> User: ..."},
    )

    assert result["conflict_type"] == "merge_conflict"
    assert "get_user" in result["resolved_code"]
    mock_client.invoke_model.assert_called_once()
    call_kwargs = mock_client.invoke_model.call_args.kwargs
    assert call_kwargs["modelId"] == HELM_MODEL


@patch("helm.invoke_arbitrator")
def test_arbitrate_uses_agentcore_when_arn_set(mock_invoke, monkeypatch):
    monkeypatch.delenv("HELM_MOCK_BEDROCK", raising=False)
    monkeypatch.setenv(
        "HELM_ARBITRATOR_ARN",
        "arn:aws:bedrock-agentcore:us-east-1:123:runtime/x",
    )

    mock_invoke.return_value = {
        "conflict_type": "merge_conflict",
        "reasoning": "via runtime",
        "resolved_code": "def x(): pass",
        "tokens_saved_estimate": "~1",
    }

    result = arbitrate(
        agent_a={"intent": "a", "code": "a"},
        agent_b={"intent": "b", "code": "b"},
        session_id="sess-1",
    )

    assert result["reasoning"] == "via runtime"
    mock_invoke.assert_called_once()
    assert mock_invoke.call_args.kwargs["session_id"] == "sess-1"


@patch("helm.invoke_anthropic_messages")
def test_arbitrate_intent_uses_tracked_invoke(mock_invoke, monkeypatch):
    monkeypatch.delenv("HELM_MOCK_BEDROCK", raising=False)
    monkeypatch.delenv("HELM_ARBITRATOR_ARN", raising=False)

    model_json = json.dumps(
        {
            "conflict_type": "intent_conflict",
            "reasoning": "compromise",
            "resolved_code": "directive",
            "tokens_saved_estimate": "~1800",
        }
    )
    mock_invoke.return_value = (model_json, _usage())

    result = arbitrate(
        {"intent": "max performance", "code": "# a"},
        {"intent": "min dependencies", "code": "# b"},
        conflict_kind="intent",
    )
    assert result["conflict_type"] == "intent_conflict"
    assert result["_usage"]["input_tokens"] == 10


def test_arbitrate_intent_conflict_mock(monkeypatch):
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "1")
    result = arbitrate(
        {"intent": "max performance", "code": "# a"},
        {"intent": "min dependencies", "code": "# b"},
        conflict_kind="intent",
    )
    assert result["conflict_type"] == "intent_conflict"


def test_arbitrate_guardrail_mock(monkeypatch):
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "1")
    result = arbitrate(
        {"intent": "keep cache", "code": "# keep"},
        {"intent": "delete cache", "code": "# delete"},
        conflict_kind="guardrail",
        guardrail_context={
            "proposed_action": {"description": "Remove cache"},
            "rule": "reverses_recent_decision",
            "message": "blocked",
        },
    )
    assert result["conflict_type"] == "proactive_guardrail"
    assert result["verdict"] == "modify"
