from benchmarks.collector import RunReport
from benchmarks.report import compare_reports


def test_compare_independent_verdict_pass():
    baseline = RunReport(
        run_id="off",
        suite="independent",
        helm_enabled=False,
        wall_clock_seconds=100.0,
        helm_api_calls=0,
        intents_declared=0,
        guardrails_blocked=0,
        conflicts_resolved=0,
        git_conflict_files=0,
        merge_success=True,
        agent_commits=[],
        tokens_saved_display="n/a",
    )
    helm_on = RunReport(
        run_id="on",
        suite="independent",
        helm_enabled=True,
        wall_clock_seconds=105.0,
        helm_api_calls=2,
        intents_declared=3,
        guardrails_blocked=0,
        conflicts_resolved=0,
        git_conflict_files=0,
        merge_success=True,
        agent_commits=[],
        tokens_saved_display="n/a",
    )
    md, passed = compare_reports(baseline, helm_on)
    assert passed
    assert "PASS" in md
