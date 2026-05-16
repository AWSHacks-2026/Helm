import json
from unittest.mock import MagicMock, patch

from bedrock.invoke_tracked import InvokeUsage
from overlord import OVERLORD_MODEL, arbitrate


def _usage() -> InvokeUsage:
    return InvokeUsage("m", "overlord", 10, 5, 1)


@patch("overlord.invoke_anthropic_messages")
def test_arbitrate_returns_parsed_resolution(mock_invoke, monkeypatch):
    monkeypatch.delenv("OVERLORD_MOCK_BEDROCK", raising=False)

    model_json = json.dumps(
        {
            "conflict_type": "merge_conflict",
            "reasoning": "Kept cache and type hints.",
            "resolved_code": "def get_user(user_id: str) -> User:\n    ...",
            "tokens_saved_estimate": "~2400",
        }
    )
    mock_invoke.return_value = (model_json, _usage())

    result = arbitrate(
        agent_a={"intent": "cache", "code": "def get_user(user_id): ..."},
        agent_b={"intent": "types", "code": "def get_user(user_id: str) -> User: ..."},
    )

    assert result["conflict_type"] == "merge_conflict"
    assert "get_user" in result["resolved_code"]
    assert result["_usage"]["input_tokens"] == 10

    mock_invoke.assert_called_once()
    assert mock_invoke.call_args.kwargs["model_id"] == OVERLORD_MODEL


@patch("overlord.invoke_anthropic_messages")
def test_arbitrate_attaches_usage_when_not_mock(mock_invoke, monkeypatch):
    monkeypatch.delenv("OVERLORD_MOCK_BEDROCK", raising=False)
    model_json = json.dumps(
        {
            "conflict_type": "merge_conflict",
            "reasoning": "r",
            "resolved_code": "def f(): pass",
            "tokens_saved_estimate": "0",
        }
    )
    mock_invoke.return_value = (model_json, InvokeUsage("m", "overlord", 10, 5, 1))

    result = arbitrate({"intent": "a", "code": "a"}, {"intent": "b", "code": "b"})
    assert result["_usage"]["input_tokens"] == 10


def test_arbitrate_intent_conflict_mock(monkeypatch):
    monkeypatch.setenv("OVERLORD_MOCK_BEDROCK", "1")
    result = arbitrate(
        {"intent": "max performance", "code": "# a"},
        {"intent": "min dependencies", "code": "# b"},
        conflict_kind="intent",
    )
    assert result["conflict_type"] == "intent_conflict"


def test_arbitrate_guardrail_mock(monkeypatch):
    monkeypatch.setenv("OVERLORD_MOCK_BEDROCK", "1")
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
