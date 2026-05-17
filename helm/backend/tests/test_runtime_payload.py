import sys
from pathlib import Path

import pytest

_ARBITRATOR = Path(__file__).resolve().parents[2] / "agentcore" / "arbitrator"
sys.path.insert(0, str(_ARBITRATOR))

from runtime_logic import parse_invoke_request  # noqa: E402

_PAYLOAD = {
    "agent_a": {"intent": "cache", "code": "def get_user(id): ..."},
    "agent_b": {"intent": "types", "code": "def get_user(id: str): ..."},
}


def test_parse_invoke_request_accepts_direct_shape():
    a, b, kb = parse_invoke_request({**_PAYLOAD, "kb_context": []})
    assert a["intent"] == "cache"
    assert b["intent"] == "types"
    assert kb == []


def test_parse_invoke_request_accepts_cli_prompt_wrapper():
    import json

    a, b, _ = parse_invoke_request({"prompt": json.dumps(_PAYLOAD)})
    assert a["code"].startswith("def get_user")


def test_parse_invoke_request_rejects_empty_agent():
    with pytest.raises(ValueError, match="Invalid payload"):
        parse_invoke_request({"agent_a": {}, "agent_b": {}})
