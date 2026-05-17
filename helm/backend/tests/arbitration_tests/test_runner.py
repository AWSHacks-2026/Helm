import json
from unittest.mock import MagicMock, patch

from arbitration.runner import HELM_MODEL, run_arbitration


def _bedrock_body(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


@patch("arbitration.runner.get_bedrock_client")
def test_run_arbitration_returns_validated_dict(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    model_json = json.dumps(
        {
            "conflict_type": "merge_conflict",
            "reasoning": "Merged cache and type hints.",
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

    result = run_arbitration(
        agent_a={"intent": "cache", "code": "def get_user(user_id): ..."},
        agent_b={"intent": "types", "code": "def get_user(user_id: str) -> User: ..."},
        kb_context=None,
    )

    assert result["conflict_type"] == "merge_conflict"
    assert "get_user" in result["resolved_code"]
    mock_client.invoke_model.assert_called_once()
    assert mock_client.invoke_model.call_args.kwargs["modelId"] == HELM_MODEL
