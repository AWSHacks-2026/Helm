import json
from unittest.mock import MagicMock, patch

from agents.usage_ledger import UsageLedger
from bedrock.invoke_tracked import InvokeUsage, invoke_anthropic_messages


def test_usage_ledger_totals():
    ledger = UsageLedger()
    ledger.add(InvokeUsage("m1", "agent_a", 100, 50, 10))
    ledger.add(InvokeUsage("m1", "agent_b", 200, 80, 20))
    assert ledger.total_input_tokens == 300
    assert ledger.total_output_tokens == 130
    assert ledger.total_tokens == 430
    assert len(ledger.calls) == 2


def test_invoke_anthropic_messages_parses_usage(monkeypatch):
    monkeypatch.delenv("OVERLORD_MOCK_BEDROCK", raising=False)
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(
        {
            "content": [{"text": "def f(): pass"}],
            "usage": {"input_tokens": 42, "output_tokens": 7},
        }
    ).encode()
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = {"body": mock_body}

    with patch("bedrock.invoke_tracked.get_bedrock_client", return_value=mock_client):
        text, usage = invoke_anthropic_messages(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=100,
            role="agent_a",
        )

    assert text == "def f(): pass"
    assert usage.input_tokens == 42
    assert usage.output_tokens == 7
    assert usage.role == "agent_a"
