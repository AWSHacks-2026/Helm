from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal

from bedrock.intent_overlap import intent_overlap_score, intents_conflict, path_prefix_overlap
from store.sessions import SessionStore

GateTier = Literal["allow", "triage", "arbitrate"]
ContentionKind = Literal["dedup", "intent", "merge", "guardrail"] | None


@dataclass
class ContentionAssessment:
    contention_detected: bool
    contention_kind: ContentionKind
    gate_tier: GateTier
    signals: list[str] = field(default_factory=list)
    peers: list[str] = field(default_factory=list)
    file_clusters: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contention_detected": self.contention_detected,
            "contention_kind": self.contention_kind,
            "gate_tier": self.gate_tier,
            "signals": self.signals,
            "peers": self.peers,
            "file_clusters": self.file_clusters,
            "coordination_recommended": self.gate_tier != "allow",
        }


def gate_enabled() -> bool:
    return os.getenv("HELM_GATE_ENABLED", "1") == "1"


def gate_force() -> bool:
    return os.getenv("HELM_GATE_FORCE", "0") == "1"


def _min_agents() -> int:
    return int(os.getenv("HELM_GATE_MIN_AGENTS", "2"))


def _overlap_threshold() -> float:
    return float(os.getenv("HELM_GATE_INTENT_OVERLAP", "0.35"))


def _triage_enabled() -> bool:
    return os.getenv("HELM_GATE_TRIAGE", "0") == "1"


def _allow() -> ContentionAssessment:
    return ContentionAssessment(
        contention_detected=False,
        contention_kind=None,
        gate_tier="allow",
    )


def _arbitrate(
    kind: ContentionKind,
    signals: list[str],
    peers: list[str],
    clusters: dict[str, list[str]],
) -> ContentionAssessment:
    return ContentionAssessment(
        contention_detected=True,
        contention_kind=kind,
        gate_tier="arbitrate",
        signals=signals,
        peers=peers,
        file_clusters=clusters,
    )


def _clusters_from_file_paths(
    file_paths: dict[str, str], min_agents: int
) -> dict[str, list[str]]:
    by_path: dict[str, list[str]] = {}
    for aid, path in file_paths.items():
        agents = by_path.setdefault(path, [])
        if aid not in agents:
            agents.append(aid)
    return {path: agents for path, agents in by_path.items() if len(agents) >= min_agents}


def assess_dedup(
    session_store: SessionStore,
    session_id: str,
    *,
    agents: dict[str, dict[str, Any]],
    file_paths: dict[str, str],
) -> ContentionAssessment:
    min_agents = _min_agents()
    clusters = session_store.file_clusters(session_id, min_agents=min_agents)
    if not clusters:
        clusters = _clusters_from_file_paths(file_paths, min_agents)

    if not gate_enabled() or gate_force():
        return _arbitrate("dedup", ["gate_bypass"], list(agents), clusters)

    if not clusters:
        return _allow()

    signals: list[str] = []
    peers: list[str] = []
    for path, agent_list in clusters.items():
        signals.append(f"file_cluster:{path}:{len(agent_list)}")
        for aid in agent_list:
            if aid not in peers:
                peers.append(aid)

    return _arbitrate("dedup", signals, peers, clusters)


def assess_intent(
    session_store: SessionStore,
    session_id: str,
    *,
    agent_id: str,
    file_path: str,
    intent: str,
) -> ContentionAssessment:
    if not gate_enabled() or gate_force():
        return _arbitrate("intent", ["gate_bypass"], [], {})

    others = session_store.intents_on_file(session_id, file_path, exclude=agent_id)
    if not others:
        return _allow()

    clusters = session_store.file_clusters(session_id, min_agents=_min_agents())
    signals = [f"file_overlap:{file_path}"]
    peers = [o["agent_id"] for o in others]

    if others and not any(
        intents_conflict(other["intent"], intent)
        or intent_overlap_score(other["intent"], intent) >= _overlap_threshold()
        for other in others
    ):
        return _arbitrate(
            "intent",
            signals + ["same_file_peer"],
            peers,
            clusters,
        )

    for other in others:
        if intents_conflict(other["intent"], intent):
            return _arbitrate(
                "intent",
                signals + ["intent_contradiction"],
                peers,
                clusters,
            )
        score = intent_overlap_score(other["intent"], intent)
        if score >= _overlap_threshold():
            return _arbitrate(
                "intent",
                signals + [f"intent_overlap:{score:.2f}"],
                peers,
                clusters,
            )

    if _triage_enabled():
        for other in others:
            other_path = other.get("file_path", file_path)
            if path_prefix_overlap(file_path, other_path) and file_path != other_path:
                fail_closed = os.getenv("HELM_GATE_FAIL_MODE", "open") == "closed"
                tier: GateTier = "arbitrate" if fail_closed else "triage"
                return ContentionAssessment(
                    contention_detected=True,
                    contention_kind="intent",
                    gate_tier=tier,
                    signals=signals + ["path_prefix_overlap"],
                    peers=peers,
                    file_clusters=clusters,
                )

    return _allow()


def log_gate_skip(session_id: str, assessment: ContentionAssessment) -> None:
    if os.getenv("HELM_GATE_LOG_SKIPS", "1") != "1":
        return
    if assessment.gate_tier != "allow":
        return
    try:
        from bedrock import knowledge_base as kb

        kb.append_event(
            session_id,
            {
                "event_type": "contention_gate",
                "payload": assessment.to_dict(),
            },
        )
    except Exception:
        pass


def skipped_dedup_result(agent_ids: list[str]) -> dict[str, Any]:
    """No Bedrock — all agents continue without duplicate_detected."""
    return {
        "duplicate_detected": False,
        "conflict_type": "duplicate_work",
        "reasoning": "contention_gate: no file clusters >= min agents",
        "agent_to_continue": agent_ids[0] if agent_ids else "agent_a",
        "agent_to_reassign": agent_ids[-1] if len(agent_ids) > 1 else "agent_b",
        "continuations": list(agent_ids),
        "reassignments": [],
        "gate_skipped": True,
    }
