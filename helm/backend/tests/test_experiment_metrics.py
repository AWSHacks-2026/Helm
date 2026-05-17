import os

os.environ["HELM_MOCK_BEDROCK"] = "1"

from experiments.metrics import (
    AgentRunResult,
    ThemeRunResult,
    count_conflict_edits,
    count_reverted_commits,
    merge_success_rate,
    sequential_merge_build_ok,
    total_resolution_ms,
    total_tokens,
)


def test_conflict_edits_detects_divergent_outputs():
    runs = [
        AgentRunResult("a", "f.py", "x = 1", 0, 0, 10, True),
        AgentRunResult("b", "f.py", "y = 2", 0, 0, 10, True),
        AgentRunResult("a", "other.py", "same", 0, 0, 10, True),
    ]
    assert count_conflict_edits(runs) == 1


def test_reverted_commits_detects_overwrite():
    base = {"f.py": "shared base\n"}
    runs = [
        AgentRunResult(
            "agent_alpha",
            "f.py",
            "shared base\nalpha unique block that is long enough to detect",
            0,
            0,
            10,
            True,
        ),
        AgentRunResult("agent_beta", "f.py", "shared base\nbeta only", 0, 0, 10, True),
    ]
    assert count_reverted_commits(base, runs) == 1


def test_sequential_merge_counts_parsable_files():
    base = {"ok.py": "print('ok')\n"}
    runs = [
        AgentRunResult("a", "ok.py", "print('ok')\n", 0, 0, 10, True),
        AgentRunResult("b", "ok.py", "print('ok')\ndef broken(", 0, 0, 10, False),
    ]
    parsed, total = sequential_merge_build_ok(base, runs)
    assert parsed == 0
    assert total == 1


def test_total_tokens_and_time():
    runs = [
        AgentRunResult("a", "f.py", "x", 10, 100, 50, True),
        AgentRunResult("b", "f.py", "y", 20, 200, 60, True),
    ]
    assert total_tokens(runs) == 410
    assert total_resolution_ms(runs) == 30
