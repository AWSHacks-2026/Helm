from __future__ import annotations

import pytest

from agents.shopfix_guardrail_benchmark import run_shopfix_guardrail_benchmark


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "1")
    monkeypatch.setenv("HELM_USE_LOCAL_MEMORY", "true")
    monkeypatch.setenv("HELM_USE_LOCAL_POLICY", "true")
    monkeypatch.setenv("SHOPFIX_SKIP_VERIFY", "1")


def test_shopfix_guardrail_blocks_destructive_action(tmp_path):
    result = run_shopfix_guardrail_benchmark(work_dir=tmp_path)
    assert result["comparison"]["helm_blocked_action"] is True
    assert result["helm"]["blocked_rule"] in {
        "reverses_recent_decision",
        "file_overlap",
        "intent_contradiction",
    }
    assert result["baseline"]["executed"] is True
    assert result["helm"]["executed"] is False
