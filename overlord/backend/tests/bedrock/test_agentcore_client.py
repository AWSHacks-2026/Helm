import json
from unittest.mock import MagicMock, patch

from bedrock.agentcore_client import (
    invoke_arbitrator,
    normalize_runtime_session_id,
    parse_agentcore_response,
)


def test_normalize_runtime_session_id_short_ids():
    short = "demo-merge_conflict"
    normalized = normalize_runtime_session_id(short)
    assert len(normalized) >= 33
    assert normalize_runtime_session_id(short) == normalized


def test_normalize_runtime_session_id_preserves_long_ids():
    long_id = "a" * 40
    assert normalize_runtime_session_id(long_id) == long_id


def test_parse_agentcore_response_json_body():
    chunks = [
        json.dumps(
            {
                "conflict_type": "merge_conflict",
                "reasoning": "ok",
                "resolved_code": "x",
                "tokens_saved_estimate": "1",
            }
        ).encode()
    ]
    result = parse_agentcore_response(
        {"contentType": "application/json", "response": chunks}
    )
    assert result["conflict_type"] == "merge_conflict"


@patch("bedrock.agentcore_client.get_agentcore_client")
def test_invoke_arbitrator_sends_payload_and_session(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.invoke_agent_runtime.return_value = {
        "contentType": "application/json",
        "response": [
            json.dumps(
                {
                    "conflict_type": "merge_conflict",
                    "reasoning": "Merged.",
                    "resolved_code": "def f(): pass",
                    "tokens_saved_estimate": "~100",
                }
            ).encode()
        ],
    }

    result = invoke_arbitrator(
        agent_runtime_arn="arn:aws:bedrock-agentcore:us-east-1:123:runtime/test",
        session_id="sess-abc",
        agent_a={"intent": "a", "code": "a"},
        agent_b={"intent": "b", "code": "b"},
        kb_context=[{"text": "prior intent"}],
    )

    assert result["resolved_code"] == "def f(): pass"
    call_kwargs = mock_client.invoke_agent_runtime.call_args.kwargs
    assert call_kwargs["agentRuntimeArn"].endswith("runtime/test")
    assert call_kwargs["runtimeSessionId"] == normalize_runtime_session_id("sess-abc")
    payload = json.loads(call_kwargs["payload"].decode())
    assert payload["agent_a"]["intent"] == "a"
    assert payload["kb_context"] == [{"text": "prior intent"}]
