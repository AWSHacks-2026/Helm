import json
from unittest.mock import MagicMock, patch

from overlord import OVERLORD_MODEL, arbitrate


def _bedrock_body(text: str) -> dict:
    return {
        "content": [{"type": "text", "text": text}],
    }


@patch("overlord.get_bedrock_client")
def test_arbitrate_returns_parsed_resolution(mock_get_client):
    import os

    os.environ.pop("OVERLORD_MOCK_BEDROCK", None)

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
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps(_bedrock_body(model_json)).encode()
            )
        )
    }

    result = arbitrate(
        agent_a={"intent": "cache", "code": "def get_user(user_id): ..."},
        agent_b={"intent": "types", "code": "def get_user(user_id: str) -> User: ..."},
    )

    assert result["conflict_type"] == "merge_conflict"
    assert "cache" in result["reasoning"].lower() or "type" in result["reasoning"].lower()
    assert "get_user" in result["resolved_code"]

    mock_client.invoke_model.assert_called_once()
    call_kwargs = mock_client.invoke_model.call_args.kwargs
    assert call_kwargs["modelId"] == OVERLORD_MODEL
    body = json.loads(call_kwargs["body"])
    assert body["anthropic_version"] == "bedrock-2023-05-31"
    assert body["max_tokens"] >= 1000


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
