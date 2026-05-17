from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from agents.haiku_agent import agent_model_id
from bedrock.invoke_tracked import InvokeUsage
from bedrock.invoke_tracked import invoke_anthropic_messages


AGENT_COUNTS = (2, 4, 8, 16)
REALISTIC_OVERLAP_PROFILE = "realistic-overlap"
WORST_CASE_PROFILE = "worst-case"
BenchmarkProfile = Literal["realistic-overlap", "worst-case"]
TEST_PROMPT = (
    "Build a full-stack e-commerce platform with user authentication, "
    "product catalog, shopping cart, payment processing, order management, "
    "inventory tracking, admin dashboard, and a recommendation engine."
)
HELM_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = HELM_ROOT / "demo"


@dataclass(frozen=True)
class BenchmarkConfig:
    agent_counts: tuple[int, ...] = AGENT_COUNTS
    output_dir: Path = DEFAULT_OUTPUT_DIR
    max_tokens: int = 700
    allow_mock: bool = False
    show_progress: bool = True
    profile: BenchmarkProfile = REALISTIC_OVERLAP_PROFILE


@dataclass(frozen=True)
class BenchmarkRow:
    agent_count: int
    without_helm_tokens: int
    with_helm_tokens: int
    without_helm_seconds: float
    with_helm_seconds: float
    without_helm_build_rate: float
    with_helm_build_rate: float
    without_helm_conflicting_edits: int
    with_helm_conflicting_edits: int
    without_helm_reverted_commits: int
    with_helm_reverted_commits: int

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def build_agent_intent(index: int) -> str:
    return f"agent_{index:02d}: {TEST_PROMPT}"


def build_agent_conflict_prompt(
    *,
    agent_id: str,
    peer_id: str,
    agent_intent: str,
    peer_intent: str,
) -> str:
    return (
        "Two coding agents are about to work on overlapping parts of the same "
        "full-stack e-commerce platform.\n\n"
        f"{agent_id} intent:\n{agent_intent}\n\n"
        f"{peer_id} intent:\n{peer_intent}\n\n"
        "Identify likely duplicate work, merge conflicts, and coordination risks. "
        "Return a concise conflict-resolution plan that preserves the highest-value "
        "work from both agents."
    )


def build_helm_agents(agent_count: int) -> tuple[dict, dict]:
    intents = [build_agent_intent(index) for index in range(1, agent_count + 1)]
    midpoint = agent_count // 2
    shared_intent = "Coordinate duplicated e-commerce build work."
    return (
        {"intent": shared_intent, "code": "\n".join(intents[:midpoint])},
        {"intent": shared_intent, "code": "\n".join(intents[midpoint:])},
    )


def _agent_ids(agent_count: int) -> list[str]:
    return [f"agent_{index:02d}" for index in range(1, agent_count + 1)]


def _realistic_clusters(agent_count: int) -> list[list[str]]:
    agent_ids = _agent_ids(agent_count)
    if agent_count <= 2:
        sizes = [agent_count]
    elif agent_count <= 4:
        sizes = [2, agent_count - 2]
    elif agent_count <= 8:
        sizes = [3, 3, agent_count - 6]
    else:
        # Approximate real project overlap zones: auth, commerce, catalog, admin/ML.
        base_sizes = [4, 5, 4, 3]
        sizes = []
        remaining = agent_count
        for size in base_sizes:
            if remaining <= 0:
                break
            sizes.append(min(size, remaining))
            remaining -= size
        if remaining > 0:
            sizes[-1] += remaining

    clusters: list[list[str]] = []
    cursor = 0
    for size in sizes:
        if size <= 0:
            continue
        clusters.append(agent_ids[cursor : cursor + size])
        cursor += size
    return clusters


def _validate_profile(profile: str) -> BenchmarkProfile:
    if profile not in {REALISTIC_OVERLAP_PROFILE, WORST_CASE_PROFILE}:
        raise ValueError(
            f"profile must be {REALISTIC_OVERLAP_PROFILE!r} or {WORST_CASE_PROFILE!r}"
        )
    return profile  # type: ignore[return-value]


def create_conflict_pairs(
    *,
    agent_count: int,
    profile: BenchmarkProfile,
) -> list[tuple[str, str]]:
    _validate_profile(profile)
    if profile == WORST_CASE_PROFILE:
        agent_ids = _agent_ids(agent_count)
        return [
            (agent_id, peer_id)
            for agent_id in agent_ids
            for peer_id in agent_ids
            if agent_id != peer_id
        ]

    pairs: list[tuple[str, str]] = []
    for cluster in _realistic_clusters(agent_count):
        pairs.extend(
            (agent_id, peer_id)
            for agent_id in cluster
            for peer_id in cluster
            if agent_id != peer_id
        )
    return pairs


def build_helm_coordination_pairs(
    *,
    agent_count: int,
    profile: BenchmarkProfile,
) -> list[tuple[str, str]]:
    _validate_profile(profile)
    if profile == WORST_CASE_PROFILE:
        return [("agent_01", peer_id) for peer_id in _agent_ids(agent_count)[1:]]

    pairs: list[tuple[str, str]] = []
    for cluster in _realistic_clusters(agent_count):
        lead_id = cluster[0]
        pairs.extend((lead_id, peer_id) for peer_id in cluster[1:])
    return pairs


def count_conflicting_edits(outputs: dict[str, str]) -> int:
    overlapping_outputs = [
        output
        for output in outputs.values()
        if "auth" in output.lower() or "user" in output.lower()
    ]
    return 1 if len(overlapping_outputs) >= 2 else 0


def count_reverted_commits(
    *,
    agent_count: int,
    with_helm: bool,
    outputs: dict[str, str] | None = None,
) -> int:
    if outputs is not None:
        return sum(1 for output in outputs.values() if "revert" in output.lower())
    return 0


def _sum_tokens(usages: list[InvokeUsage]) -> int:
    return sum(usage.input_tokens + usage.output_tokens for usage in usages)


def _validate_agent_count(agent_count: int) -> None:
    if agent_count < 2:
        raise ValueError("agent_count must be at least 2 for conflict benchmarking")


def _require_usage_tokens(usage: InvokeUsage, *, source: str) -> None:
    if usage.input_tokens <= 0 or usage.output_tokens <= 0:
        raise RuntimeError(
            f"{source} did not return positive Bedrock usage token counts"
        )


def _build_rate(*, successful_calls: int, planned_calls: int) -> float:
    if planned_calls <= 0:
        return 0.0
    return successful_calls / planned_calls


def _progress(iterable, *, total: int, desc: str, enabled: bool):
    if not enabled:
        return iterable

    from tqdm import tqdm

    return tqdm(iterable, total=total, desc=desc, unit="req")


def _usage_to_dict(usage: InvokeUsage) -> dict[str, int | str]:
    return {
        "model_id": usage.model_id,
        "role": usage.role,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "latency_ms": usage.latency_ms,
    }


def arbitrate(agent_a: dict, agent_b: dict, **kwargs) -> dict:
    from helm import arbitrate as helm_arbitrate

    return helm_arbitrate(agent_a, agent_b, **kwargs)


def run_without_helm(
    *,
    agent_count: int,
    max_tokens: int,
    profile: BenchmarkProfile = REALISTIC_OVERLAP_PROFILE,
    show_progress: bool = False,
) -> dict:
    _validate_agent_count(agent_count)
    profile = _validate_profile(profile)
    started = time.perf_counter()
    intents = {
        f"agent_{index:02d}": build_agent_intent(index)
        for index in range(1, agent_count + 1)
    }
    usages: list[InvokeUsage] = []
    outputs: dict[str, str] = {}
    pair_ids = create_conflict_pairs(agent_count=agent_count, profile=profile)
    planned_calls = len(pair_ids)

    pairs = [
        (agent_id, intents[agent_id], peer_id, intents[peer_id])
        for agent_id, peer_id in pair_ids
    ]

    for agent_id, agent_intent, peer_id, peer_intent in _progress(
        pairs,
        total=planned_calls,
        desc=f"Without Helm {profile} N={agent_count}",
        enabled=show_progress,
    ):
        prompt = build_agent_conflict_prompt(
            agent_id=agent_id,
            peer_id=peer_id,
            agent_intent=agent_intent,
            peer_intent=peer_intent,
        )
        output, usage = invoke_anthropic_messages(
            model_id=agent_model_id(),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            role=agent_id,
        )
        _require_usage_tokens(usage, source="Agent Haiku resolution")
        usages.append(usage)
        outputs[f"{agent_id}->{peer_id}"] = output

    seconds = time.perf_counter() - started
    return {
        "tokens": _sum_tokens(usages),
        "seconds": seconds,
        "build_rate": _build_rate(
            successful_calls=len(usages),
            planned_calls=planned_calls,
        ),
        "conflicting_edits": count_conflicting_edits(outputs),
        "reverted_commits": count_reverted_commits(
            agent_count=agent_count,
            with_helm=False,
            outputs=outputs,
        ),
        "calls": [_usage_to_dict(usage) for usage in usages],
    }


def _usage_from_arbitration_result(result: dict, *, allow_mock: bool = False) -> InvokeUsage:
    raw_usage = result.get("_usage")
    if not raw_usage:
        if allow_mock and os.getenv("HELM_MOCK_BEDROCK") == "1":
            payload = json.dumps(result)
            reasoning = str(result.get("reasoning", "mock Helm arbitration"))
            return InvokeUsage(
                model_id="mock-helm",
                role="helm",
                input_tokens=max(1, len(payload) // 4),
                output_tokens=max(1, len(reasoning) // 4),
                latency_ms=0,
            )
        raise RuntimeError(
            "Token benchmark requires tracked Bedrock arbitration with _usage."
        )

    required_keys = {"model_id", "input_tokens", "output_tokens", "latency_ms"}
    missing_keys = required_keys.difference(raw_usage)
    if missing_keys:
        raise RuntimeError(
            "Token benchmark arbitration _usage is missing required fields: "
            + ", ".join(sorted(missing_keys))
        )

    usage = InvokeUsage(
        model_id=str(raw_usage["model_id"]),
        role="helm",
        input_tokens=int(raw_usage["input_tokens"]),
        output_tokens=int(raw_usage["output_tokens"]),
        latency_ms=int(raw_usage["latency_ms"]),
    )
    _require_usage_tokens(usage, source="Helm arbitration")
    return usage


def run_with_helm(
    *,
    agent_count: int,
    allow_mock: bool = False,
    profile: BenchmarkProfile = REALISTIC_OVERLAP_PROFILE,
    show_progress: bool = False,
) -> dict:
    _validate_agent_count(agent_count)
    profile = _validate_profile(profile)
    started = time.perf_counter()
    intents = {
        f"agent_{index:02d}": build_agent_intent(index)
        for index in range(1, agent_count + 1)
    }
    usages: list[InvokeUsage] = []
    outputs: dict[str, str] = {}
    pairs = build_helm_coordination_pairs(
        agent_count=agent_count,
        profile=profile,
    )
    planned_calls = len(pairs)

    for lead_id, peer_id in _progress(
        pairs,
        total=planned_calls,
        desc=f"With Helm {profile} N={agent_count}",
        enabled=show_progress,
    ):
        lead_agent = {"intent": intents[lead_id], "code": intents[lead_id]}
        peer_agent = {"intent": intents[peer_id], "code": intents[peer_id]}
        result = arbitrate(
            lead_agent,
            peer_agent,
            conflict_kind="intent",
            session_id=f"token-benchmark-{profile}-{agent_count}-{lead_id}-{peer_id}",
        )
        usages.append(_usage_from_arbitration_result(result, allow_mock=allow_mock))
        outputs[peer_id] = " ".join(
            str(result.get(key, "")) for key in ("reasoning", "resolved_code")
        )

    seconds = time.perf_counter() - started
    return {
        "tokens": _sum_tokens(usages),
        "seconds": seconds,
        "build_rate": _build_rate(
            successful_calls=len(usages),
            planned_calls=planned_calls,
        ),
        "conflicting_edits": count_conflicting_edits(outputs),
        "reverted_commits": count_reverted_commits(
            agent_count=agent_count,
            with_helm=True,
            outputs=outputs,
        ),
        "calls": [_usage_to_dict(usage) for usage in usages],
    }


def run_benchmark_matrix(config: BenchmarkConfig) -> list[BenchmarkRow]:
    if os.getenv("HELM_MOCK_BEDROCK") == "1" and not config.allow_mock:
        raise RuntimeError("Benchmark requires real Bedrock token usage.")

    rows: list[BenchmarkRow] = []
    for agent_count in config.agent_counts:
        without_helm = run_without_helm(
            agent_count=agent_count,
            max_tokens=config.max_tokens,
            profile=config.profile,
            show_progress=config.show_progress,
        )
        with_helm = run_with_helm(
            agent_count=agent_count,
            allow_mock=config.allow_mock,
            profile=config.profile,
            show_progress=config.show_progress,
        )
        rows.append(
            BenchmarkRow(
                agent_count=agent_count,
                without_helm_tokens=int(without_helm["tokens"]),
                with_helm_tokens=int(with_helm["tokens"]),
                without_helm_seconds=float(without_helm["seconds"]),
                with_helm_seconds=float(with_helm["seconds"]),
                without_helm_build_rate=float(without_helm["build_rate"]),
                with_helm_build_rate=float(with_helm["build_rate"]),
                without_helm_conflicting_edits=int(
                    without_helm["conflicting_edits"]
                ),
                with_helm_conflicting_edits=int(
                    with_helm["conflicting_edits"]
                ),
                without_helm_reverted_commits=int(
                    without_helm["reverted_commits"]
                ),
                with_helm_reverted_commits=int(
                    with_helm["reverted_commits"]
                ),
            )
        )
    return rows


def _output_stem(profile: BenchmarkProfile | None = None) -> str:
    if profile is None:
        return "helm-token-benchmark"
    return f"helm-token-benchmark-{_validate_profile(profile)}"


def write_results_json(
    rows: list[BenchmarkRow],
    output_dir: Path,
    *,
    profile: BenchmarkProfile | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_output_stem(profile)}.json"
    payload: list[dict[str, int | float]] | dict[str, object]
    if profile is None:
        payload = [row.to_dict() for row in rows]
    else:
        payload = {
            "profile": _validate_profile(profile),
            "rows": [row.to_dict() for row in rows],
        }
    path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return path


def save_benchmark_figure(
    rows: list[BenchmarkRow],
    output_dir: Path,
    *,
    profile: BenchmarkProfile | None = None,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_output_stem(profile)}.png"

    agent_counts = [row.agent_count for row in rows]
    without_tokens = [row.without_helm_tokens for row in rows]
    with_tokens = [row.with_helm_tokens for row in rows]
    without_seconds = [row.without_helm_seconds for row in rows]
    with_seconds = [row.with_helm_seconds for row in rows]

    fig, axes = plt.subplots(1, 2)
    axes[0].plot(agent_counts, without_tokens, label="Without Helm")
    axes[0].plot(agent_counts, with_tokens, label="With Helm")
    axes[0].set_xlabel("Number of agents")
    axes[0].set_ylabel("Total Bedrock tokens")
    title_suffix = f" ({profile})" if profile else ""
    axes[0].set_title(f"Total Tokens vs Agents{title_suffix}")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(agent_counts, without_seconds, label="Without Helm")
    axes[1].plot(agent_counts, with_seconds, label="With Helm")
    axes[1].set_xlabel("Number of agents")
    axes[1].set_ylabel("Wall-clock seconds")
    axes[1].set_title(f"Resolution Time vs Agents{title_suffix}")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def print_summary_table(rows: list[BenchmarkRow]) -> None:
    headers = [
        "agents",
        "without_tokens",
        "with_tokens",
        "without_seconds",
        "with_seconds",
        "without_build_rate",
        "with_build_rate",
        "without_conflicts",
        "with_conflicts",
        "without_reverts",
        "with_reverts",
    ]
    print(" | ".join(headers))
    print(" | ".join("-" * len(header) for header in headers))
    for row in rows:
        values = [
            row.agent_count,
            row.without_helm_tokens,
            row.with_helm_tokens,
            f"{row.without_helm_seconds:.2f}",
            f"{row.with_helm_seconds:.2f}",
            f"{row.without_helm_build_rate:.2f}",
            f"{row.with_helm_build_rate:.2f}",
            row.without_helm_conflicting_edits,
            row.with_helm_conflicting_edits,
            row.without_helm_reverted_commits,
            row.with_helm_reverted_commits,
        ]
        print(" | ".join(str(value) for value in values))
