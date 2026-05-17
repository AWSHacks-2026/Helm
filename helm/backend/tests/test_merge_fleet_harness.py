import os

os.environ["HELM_MOCK_BEDROCK"] = "1"

from agents.merge_fleet_harness import run_merge_fleet_benchmark


def test_merge_fleet_mock_benchmark_runs():
    result = run_merge_fleet_benchmark("merge_conflict_fleet")
    c = result["comparison"]

    assert result["agent_count"] == 6
    assert c["baseline_merge_fix_calls"] >= 2
    assert result["helm"]["strategy"] == "haiku_chain"
    assert c["helm_arbitration_calls"] <= 5  # haiku merges + optional sonnet escalation
    assert result["baseline"]["files_merged"] == 3
    assert result["helm"]["files_merged"] == 3
