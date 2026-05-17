import os

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from agents.haiku_agent import build_initial_edit_prompt, build_merge_fix_prompt, run_agent_edit


def test_build_initial_edit_prompt_contains_intent_and_path():
    prompt = build_initial_edit_prompt(
        agent_id="agent_a",
        file_path="app/user.py",
        intent="add caching",
        peer_code=None,
    )
    assert "agent_a" in prompt
    assert "app/user.py" in prompt
    assert "add caching" in prompt


def test_build_merge_fix_prompt_mentions_peer():
    prompt = build_merge_fix_prompt(
        agent_id="agent_b",
        file_path="app/user.py",
        intent="add types",
        own_code="def f(): pass",
        peer_code="def f():\n    return 1",
    )
    assert "agent_b" in prompt
    assert "def f():\n    return 1" in prompt


def test_run_agent_edit_returns_code_and_usage():
    code, usage = run_agent_edit(
        agent_id="agent_a",
        file_path="app/user.py",
        intent="cache",
        peer_code=None,
    )
    assert "MOCK" in code or "def" in code.lower()
    assert usage.role == "agent_a"


def test_run_agent_edit_respects_max_tokens_override(monkeypatch):
    from unittest.mock import patch

    from bedrock.invoke_tracked import InvokeUsage

    with patch("agents.haiku_agent.invoke_anthropic_messages") as mock_invoke:
        mock_invoke.return_value = ("x = 1\n", InvokeUsage("model", "agent_a", 1, 1, 1))
        run_agent_edit(
            agent_id="agent_a",
            file_path="app/user.py",
            intent="cache",
            peer_code=None,
            max_tokens=512,
        )
        assert mock_invoke.call_args.kwargs["max_tokens"] == 512
