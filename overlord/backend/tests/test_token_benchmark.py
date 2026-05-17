from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from agents.token_benchmark import (
    AGENT_COUNTS,
    DEFAULT_OUTPUT_DIR,
    REALISTIC_OVERLAP_PROFILE,
    TEST_PROMPT,
    WORST_CASE_PROFILE,
    BenchmarkConfig,
    BenchmarkRow,
    build_agent_conflict_prompt,
    build_agent_intent,
    build_overlord_agents,
    build_overlord_coordination_pairs,
    count_conflicting_edits,
    count_reverted_commits,
    create_conflict_pairs,
    print_summary_table,
)


def test_benchmark_constants_match_demo_spec():
    assert AGENT_COUNTS == (2, 4, 8, 16)
    assert DEFAULT_OUTPUT_DIR == Path("overlord/demo")
    assert TEST_PROMPT == (
        "Build a full-stack e-commerce platform with user authentication, "
        "product catalog, shopping cart, payment processing, order management, "
        "inventory tracking, admin dashboard, and a recommendation engine."
    )


def test_benchmark_config_defaults_are_frozen():
    config = BenchmarkConfig()

    assert config.agent_counts == AGENT_COUNTS
    assert config.output_dir == Path("overlord/demo")
    assert config.max_tokens == 700
    assert config.allow_mock is False
    assert config.show_progress is True
    assert config.profile == REALISTIC_OVERLAP_PROFILE
    with pytest.raises(FrozenInstanceError):
        config.max_tokens = 100


def test_benchmark_row_to_dict_and_frozen_behavior():
    row = BenchmarkRow(
        agent_count=2,
        without_overlord_tokens=100,
        with_overlord_tokens=60,
        without_overlord_seconds=1.25,
        with_overlord_seconds=0.5,
        without_overlord_build_rate=0.0,
        with_overlord_build_rate=1.0,
        without_overlord_conflicting_edits=1,
        with_overlord_conflicting_edits=1,
        without_overlord_reverted_commits=0,
        with_overlord_reverted_commits=1,
    )

    assert row.to_dict() == {
        "agent_count": 2,
        "without_overlord_tokens": 100,
        "with_overlord_tokens": 60,
        "without_overlord_seconds": 1.25,
        "with_overlord_seconds": 0.5,
        "without_overlord_build_rate": 0.0,
        "with_overlord_build_rate": 1.0,
        "without_overlord_conflicting_edits": 1,
        "with_overlord_conflicting_edits": 1,
        "without_overlord_reverted_commits": 0,
        "with_overlord_reverted_commits": 1,
    }
    with pytest.raises(FrozenInstanceError):
        row.agent_count = 4


def test_benchmark_script_exists():
    script = Path("overlord/scripts/benchmark_overlord_tokens.py")
    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "run_benchmark_matrix" in text
    assert "--no-progress" in text
    assert "--profile" in text
    assert "show_progress" in text


def test_build_agent_intent_mentions_agent_and_project_scope():
    intent = build_agent_intent(3)

    assert "agent_03" in intent
    assert "full-stack e-commerce platform" in intent
    assert "payment processing" in intent


def test_build_agent_conflict_prompt_contains_both_agents():
    prompt = build_agent_conflict_prompt(
        agent_id="agent_01",
        peer_id="agent_02",
        agent_intent="Agent 1 works on auth.",
        peer_intent="Agent 2 works on auth.",
    )

    assert "agent_01" in prompt
    assert "agent_02" in prompt
    assert "Agent 1 works on auth." in prompt
    assert "Agent 2 works on auth." in prompt
    assert "Return a concise conflict-resolution plan" in prompt


def test_build_overlord_agents_combines_intents_for_arbitrate():
    agent_a, agent_b = build_overlord_agents(4)

    assert agent_a["intent"] == "Coordinate duplicated e-commerce build work."
    assert "agent_01" in agent_a["code"]
    assert "agent_04" in agent_b["code"]
    assert "recommendation engine" in agent_b["code"]


def test_worst_case_conflict_pairs_are_all_directed_pairs():
    pairs = create_conflict_pairs(agent_count=4, profile=WORST_CASE_PROFILE)

    assert len(pairs) == 12
    assert ("agent_01", "agent_02") in pairs
    assert ("agent_02", "agent_01") in pairs
    assert all(agent_id != peer_id for agent_id, peer_id in pairs)


def test_realistic_overlap_conflict_pairs_are_clustered():
    assert len(create_conflict_pairs(agent_count=2, profile=REALISTIC_OVERLAP_PROFILE)) == 2
    assert len(create_conflict_pairs(agent_count=4, profile=REALISTIC_OVERLAP_PROFILE)) == 4
    assert len(create_conflict_pairs(agent_count=8, profile=REALISTIC_OVERLAP_PROFILE)) == 14
    assert len(create_conflict_pairs(agent_count=16, profile=REALISTIC_OVERLAP_PROFILE)) == 50


def test_realistic_overlap_overlord_pairs_are_cluster_leads():
    pairs = build_overlord_coordination_pairs(
        agent_count=16,
        profile=REALISTIC_OVERLAP_PROFILE,
    )

    assert len(pairs) == 12
    assert ("agent_01", "agent_02") in pairs
    assert ("agent_05", "agent_06") in pairs
    assert ("agent_14", "agent_16") in pairs


def test_count_conflicting_edits_counts_observed_overlap():
    outputs = {
        "agent_01": "edit auth and cart",
        "agent_02": "edit auth and catalog",
        "agent_03": "edit inventory",
    }

    assert count_conflicting_edits(outputs) == 1


def test_count_reverted_commits_counts_discarded_outputs():
    outputs = {
        "agent_01": "keep auth work",
        "agent_02": "revert duplicate login commit",
        "agent_03": "reassign inventory work",
    }

    assert count_reverted_commits(
        agent_count=4,
        with_overlord=True,
        outputs=outputs,
    ) == 1
    assert count_reverted_commits(agent_count=4, with_overlord=True) == 0
    assert count_reverted_commits(agent_count=4, with_overlord=False) == 0


def test_print_summary_table_includes_rows(capsys):
    rows = [
        BenchmarkRow(
            agent_count=2,
            without_overlord_tokens=100,
            with_overlord_tokens=60,
            without_overlord_seconds=1.25,
            with_overlord_seconds=0.5,
            without_overlord_build_rate=0.0,
            with_overlord_build_rate=1.0,
            without_overlord_conflicting_edits=1,
            with_overlord_conflicting_edits=1,
            without_overlord_reverted_commits=0,
            with_overlord_reverted_commits=1,
        )
    ]

    print_summary_table(rows)
    output = capsys.readouterr().out
    assert "agents" in output
    assert "without_tokens" in output
    assert "with_tokens" in output
    assert "100" in output
    assert "60" in output


from bedrock.invoke_tracked import InvokeUsage


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def perf_counter(self):
        self.now += 0.25
        return self.now


def test_run_without_overlord_uses_pairwise_haiku_calls(monkeypatch):
    from agents import token_benchmark

    calls = []

    def fake_invoke(*, model_id, messages, max_tokens, role):
        calls.append((model_id, messages, max_tokens, role))
        usage = InvokeUsage(model_id, role, input_tokens=10, output_tokens=5, latency_ms=25)
        return f"{role} auth conflict output", usage

    monkeypatch.setattr(token_benchmark, "invoke_anthropic_messages", fake_invoke)
    monkeypatch.setattr(token_benchmark.time, "perf_counter", FakeClock().perf_counter)

    result = token_benchmark.run_without_overlord(
        agent_count=4,
        max_tokens=300,
        profile=token_benchmark.WORST_CASE_PROFILE,
    )

    assert len(calls) == 12
    assert result["tokens"] == 180
    assert result["seconds"] == 0.25
    assert result["conflicting_edits"] == 1
    assert result["reverted_commits"] == 0
    assert result["build_rate"] == 1.0
    assert result["calls"][0] == {
        "model_id": calls[0][0],
        "role": "agent_01",
        "input_tokens": 10,
        "output_tokens": 5,
        "latency_ms": 25,
    }


def test_run_without_overlord_uses_progress_when_enabled(monkeypatch):
    from agents import token_benchmark

    progress_calls = []

    def fake_invoke(*, model_id, messages, max_tokens, role):
        usage = InvokeUsage(model_id, role, input_tokens=10, output_tokens=5, latency_ms=25)
        return f"{role} auth conflict output", usage

    def fake_progress(iterable, *, total, desc, enabled):
        progress_calls.append({"total": total, "desc": desc, "enabled": enabled})
        return iterable

    monkeypatch.setattr(token_benchmark, "invoke_anthropic_messages", fake_invoke)
    monkeypatch.setattr(token_benchmark, "_progress", fake_progress)

    token_benchmark.run_without_overlord(
        agent_count=2,
        max_tokens=300,
        profile=token_benchmark.WORST_CASE_PROFILE,
        show_progress=True,
    )

    assert progress_calls == [
        {
            "total": 2,
            "desc": "Without Overlord worst-case N=2",
            "enabled": True,
        }
    ]


def test_run_without_overlord_rejects_missing_usage_tokens(monkeypatch):
    from agents import token_benchmark

    def fake_invoke(*, model_id, messages, max_tokens, role):
        usage = InvokeUsage(model_id, role, input_tokens=0, output_tokens=0, latency_ms=25)
        return f"{role} auth conflict output", usage

    monkeypatch.setattr(token_benchmark, "invoke_anthropic_messages", fake_invoke)

    with pytest.raises(RuntimeError, match="positive Bedrock usage token counts"):
        token_benchmark.run_without_overlord(agent_count=2, max_tokens=300)


def test_run_with_overlord_uses_existing_arbitrate(monkeypatch):
    from agents import token_benchmark

    calls = []

    def fake_arbitrate(agent_a, agent_b, **kwargs):
        calls.append((agent_a, agent_b, kwargs))
        return {
            "conflict_type": "intent_conflict",
            "reasoning": "Overlord assigns one lead and coordinates the rest.",
            "resolved_code": "Unified e-commerce build plan.",
            "tokens_saved_estimate": "real usage captured separately",
            "_usage": {
                "model_id": "sonnet",
                "input_tokens": 100,
                "output_tokens": 25,
                "latency_ms": 50,
            },
        }

    monkeypatch.setattr(token_benchmark, "arbitrate", fake_arbitrate)
    monkeypatch.setattr(token_benchmark.time, "perf_counter", FakeClock().perf_counter)

    result = token_benchmark.run_with_overlord(
        agent_count=4,
        profile=token_benchmark.WORST_CASE_PROFILE,
    )

    assert len(calls) == 3
    assert result["tokens"] == 375
    assert result["seconds"] == 0.25
    assert result["conflicting_edits"] == 0
    assert result["reverted_commits"] == 0
    assert result["build_rate"] == 1.0
    assert calls[0][2]["conflict_kind"] == "intent"
    assert calls[0][2]["session_id"] == (
        "token-benchmark-worst-case-4-agent_01-agent_02"
    )
    assert result["calls"][0] == {
        "model_id": "sonnet",
        "role": "overlord",
        "input_tokens": 100,
        "output_tokens": 25,
        "latency_ms": 50,
    }


def test_run_with_overlord_uses_progress_when_enabled(monkeypatch):
    from agents import token_benchmark

    progress_calls = []

    def fake_arbitrate(agent_a, agent_b, **kwargs):
        return {
            "_usage": {
                "model_id": "sonnet",
                "input_tokens": 100,
                "output_tokens": 25,
                "latency_ms": 50,
            }
        }

    def fake_progress(iterable, *, total, desc, enabled):
        progress_calls.append({"total": total, "desc": desc, "enabled": enabled})
        return iterable

    monkeypatch.setattr(token_benchmark, "arbitrate", fake_arbitrate)
    monkeypatch.setattr(token_benchmark, "_progress", fake_progress)

    token_benchmark.run_with_overlord(
        agent_count=4,
        profile=token_benchmark.WORST_CASE_PROFILE,
        show_progress=True,
    )

    assert progress_calls == [
        {"total": 3, "desc": "With Overlord worst-case N=4", "enabled": True}
    ]


def test_run_with_overlord_rejects_missing_usage(monkeypatch):
    from agents import token_benchmark

    monkeypatch.setattr(token_benchmark, "arbitrate", lambda *args, **kwargs: {})

    with pytest.raises(RuntimeError, match="tracked Bedrock arbitration"):
        token_benchmark.run_with_overlord(agent_count=2)


def test_run_with_overlord_rejects_malformed_usage(monkeypatch):
    from agents import token_benchmark

    def fake_arbitrate(*args, **kwargs):
        return {
            "_usage": {
                "model_id": "sonnet",
                "input_tokens": 100,
                "output_tokens": 25,
            }
        }

    monkeypatch.setattr(token_benchmark, "arbitrate", fake_arbitrate)

    with pytest.raises(RuntimeError, match="missing required fields"):
        token_benchmark.run_with_overlord(agent_count=2)


def test_runners_reject_single_agent():
    from agents import token_benchmark

    with pytest.raises(ValueError, match="agent_count must be at least 2"):
        token_benchmark.run_without_overlord(agent_count=1, max_tokens=300)
    with pytest.raises(ValueError, match="agent_count must be at least 2"):
        token_benchmark.run_with_overlord(agent_count=1)


def test_run_benchmark_matrix_rejects_mock_without_allowance(monkeypatch):
    from agents import token_benchmark

    monkeypatch.setenv("OVERLORD_MOCK_BEDROCK", "1")

    with pytest.raises(RuntimeError, match="real Bedrock token usage"):
        token_benchmark.run_benchmark_matrix(BenchmarkConfig(agent_counts=(2,)))


def test_run_benchmark_matrix_allows_mock_when_explicit(monkeypatch):
    from agents import token_benchmark

    monkeypatch.setenv("OVERLORD_MOCK_BEDROCK", "1")
    monkeypatch.setattr(
        token_benchmark,
        "run_without_overlord",
        lambda *, agent_count, max_tokens, profile, show_progress=False: {
            "tokens": 30,
            "seconds": 0.25,
            "build_rate": 0.0,
            "conflicting_edits": 1,
            "reverted_commits": 0,
        },
    )
    monkeypatch.setattr(
        token_benchmark,
        "run_with_overlord",
        lambda *, agent_count, allow_mock=False, profile, show_progress=False: {
            "tokens": 15,
            "seconds": 0.1,
            "build_rate": 1.0,
            "conflicting_edits": 1,
            "reverted_commits": 1,
        },
    )

    rows = token_benchmark.run_benchmark_matrix(
        BenchmarkConfig(agent_counts=(2,), allow_mock=True)
    )

    assert rows == [
        BenchmarkRow(
            agent_count=2,
            without_overlord_tokens=30,
            with_overlord_tokens=15,
            without_overlord_seconds=0.25,
            with_overlord_seconds=0.1,
            without_overlord_build_rate=0.0,
            with_overlord_build_rate=1.0,
            without_overlord_conflicting_edits=1,
            with_overlord_conflicting_edits=1,
            without_overlord_reverted_commits=0,
            with_overlord_reverted_commits=1,
        )
    ]


def test_run_benchmark_matrix_uses_realistic_profile_by_default(monkeypatch):
    from agents import token_benchmark

    monkeypatch.delenv("OVERLORD_MOCK_BEDROCK", raising=False)
    calls = []

    def fake_without(*, agent_count, max_tokens, profile, show_progress=False):
        calls.append(("without", agent_count, profile))
        return {
            "tokens": 30,
            "seconds": 0.25,
            "build_rate": 1.0,
            "conflicting_edits": 1,
            "reverted_commits": 0,
        }

    def fake_with(*, agent_count, allow_mock=False, profile, show_progress=False):
        calls.append(("with", agent_count, profile))
        return {
            "tokens": 15,
            "seconds": 0.1,
            "build_rate": 1.0,
            "conflicting_edits": 0,
            "reverted_commits": 0,
        }

    monkeypatch.setattr(token_benchmark, "run_without_overlord", fake_without)
    monkeypatch.setattr(token_benchmark, "run_with_overlord", fake_with)

    token_benchmark.run_benchmark_matrix(BenchmarkConfig(agent_counts=(2,)))

    assert calls == [
        ("without", 2, REALISTIC_OVERLAP_PROFILE),
        ("with", 2, REALISTIC_OVERLAP_PROFILE),
    ]


def test_write_results_json(tmp_path):
    from agents.token_benchmark import write_results_json

    row = BenchmarkRow(
        agent_count=2,
        without_overlord_tokens=100,
        with_overlord_tokens=50,
        without_overlord_seconds=2.0,
        with_overlord_seconds=1.0,
        without_overlord_build_rate=0.0,
        with_overlord_build_rate=1.0,
        without_overlord_conflicting_edits=1,
        with_overlord_conflicting_edits=1,
        without_overlord_reverted_commits=0,
        with_overlord_reverted_commits=1,
    )

    path = write_results_json([row], tmp_path)

    assert path.name == "overlord-token-benchmark.json"
    assert path.exists()
    assert '"agent_count": 2' in path.read_text(encoding="utf-8")


def test_write_results_json_includes_profile_metadata(tmp_path):
    from agents.token_benchmark import write_results_json

    row = BenchmarkRow(
        agent_count=2,
        without_overlord_tokens=100,
        with_overlord_tokens=50,
        without_overlord_seconds=2.0,
        with_overlord_seconds=1.0,
        without_overlord_build_rate=0.0,
        with_overlord_build_rate=1.0,
        without_overlord_conflicting_edits=1,
        with_overlord_conflicting_edits=1,
        without_overlord_reverted_commits=0,
        with_overlord_reverted_commits=1,
    )

    path = write_results_json([row], tmp_path, profile=REALISTIC_OVERLAP_PROFILE)
    text = path.read_text(encoding="utf-8")

    assert path.name == "overlord-token-benchmark-realistic-overlap.json"
    assert f'"profile": "{REALISTIC_OVERLAP_PROFILE}"' in text
    assert '"rows"' in text


def test_save_benchmark_figure(tmp_path):
    from agents.token_benchmark import save_benchmark_figure

    rows = [
        BenchmarkRow(
            agent_count=2,
            without_overlord_tokens=100,
            with_overlord_tokens=50,
            without_overlord_seconds=2.0,
            with_overlord_seconds=1.0,
            without_overlord_build_rate=0.0,
            with_overlord_build_rate=1.0,
            without_overlord_conflicting_edits=1,
            with_overlord_conflicting_edits=1,
            without_overlord_reverted_commits=0,
            with_overlord_reverted_commits=1,
        ),
        BenchmarkRow(
            agent_count=4,
            without_overlord_tokens=300,
            with_overlord_tokens=120,
            without_overlord_seconds=5.0,
            with_overlord_seconds=2.0,
            without_overlord_build_rate=0.0,
            with_overlord_build_rate=1.0,
            without_overlord_conflicting_edits=1,
            with_overlord_conflicting_edits=1,
            without_overlord_reverted_commits=0,
            with_overlord_reverted_commits=3,
        ),
    ]

    path = save_benchmark_figure(rows, tmp_path)

    assert path.name == "overlord-token-benchmark.png"
    assert path.exists()
    assert path.stat().st_size > 0


def test_save_benchmark_figure_uses_profile_filename(tmp_path):
    from agents.token_benchmark import save_benchmark_figure

    row = BenchmarkRow(
        agent_count=2,
        without_overlord_tokens=100,
        with_overlord_tokens=50,
        without_overlord_seconds=2.0,
        with_overlord_seconds=1.0,
        without_overlord_build_rate=0.0,
        with_overlord_build_rate=1.0,
        without_overlord_conflicting_edits=1,
        with_overlord_conflicting_edits=1,
        without_overlord_reverted_commits=0,
        with_overlord_reverted_commits=1,
    )

    path = save_benchmark_figure([row], tmp_path, profile=WORST_CASE_PROFILE)

    assert path.name == "overlord-token-benchmark-worst-case.png"
    assert path.exists()
    assert path.stat().st_size > 0
