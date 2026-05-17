import os

os.environ["HELM_MOCK_BEDROCK"] = "1"

from agents.dedup_harness import run_dedup_benchmark, run_helm_path
from agents.scenarios import get_scenario
from agents.usage_ledger import UsageLedger
from agents import dedup_harness


def test_dedup_fleet_benchmark_mock_shows_impl_savings():
    result = run_dedup_benchmark("duplicate_work_fleet")
    c = result["comparison"]

    assert c["helm_duplicate_detected"] is True
    assert c["baseline_full_implementation_runs"] == 6
    assert c["helm_full_implementation_runs"] == 3
    assert c["duplicate_implementations_avoided"] == 3
    assert len(result["helm"]["continuations"]) == 3
    assert len(result["helm"]["reassignments"]) == 3


def test_dedup_pairwise_benchmark_mock_still_works():
    result = run_dedup_benchmark("duplicate_work")
    c = result["comparison"]

    assert c["baseline_full_implementation_runs"] == 2
    assert c["helm_full_implementation_runs"] == 1
    assert c["duplicate_implementations_avoided"] == 1


def test_run_helm_path_skips_bedrock_when_disjoint(monkeypatch):
    monkeypatch.setenv("HELM_GATE_ENABLED", "1")
    monkeypatch.setenv("HELM_MOCK_BEDROCK", "1")
    scenario = get_scenario("commerce_disjoint")
    file_paths = dedup_harness._scenario_file_paths(scenario)
    ledger = UsageLedger()
    result = run_helm_path(scenario, file_paths, ledger, "commerce_disjoint")
    assert result.get("gate_skipped") is True
    assert result["dedup_resolution"].get("gate_skipped") is True
    dedup_roles = [c.role for c in ledger.calls if "dedup" in c.role]
    assert dedup_roles == []


def test_commerce_disjoint_benchmark_gate_skips_coordination(monkeypatch):
    monkeypatch.setenv("HELM_GATE_ENABLED", "1")
    result = run_dedup_benchmark("commerce_disjoint")
    assert result["helm"].get("gate_skipped") is True
    dedup_calls = [
        c
        for c in result["helm"]["usage"]["calls"]
        if "dedup" in c.get("role", "")
    ]
    assert dedup_calls == []
