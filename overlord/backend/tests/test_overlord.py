import json
from unittest.mock import MagicMock, patch

from arbitration.runner import OVERLORD_MODEL
from overlord import arbitrate


def _bedrock_body(text: str) -> dict:
    return {
        "content": [{"type": "text", "text": text}],
    }


@patch("arbitration.runner.get_bedrock_client")
def test_arbitrate_returns_parsed_resolution_legacy_path(mock_get_client):
    import os

    os.environ.pop("OVERLORD_MOCK_BEDROCK", None)
    os.environ.pop("OVERLORD_ARBITRATOR_ARN", None)

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


@patch("overlord.invoke_arbitrator")
def test_arbitrate_uses_agentcore_when_arn_set(mock_invoke):
    import os

    os.environ.pop("OVERLORD_MOCK_BEDROCK", None)
    os.environ["OVERLORD_ARBITRATOR_ARN"] = (
        "arn:aws:bedrock-agentcore:us-east-1:123:runtime/x"
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
    _, kwargs = mock_invoke.call_args
    assert kwargs["session_id"] == "sess-1"

    os.environ.pop("OVERLORD_ARBITRATOR_ARN", None)
