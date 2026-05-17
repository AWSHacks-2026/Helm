from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

# Repo root is three levels up from helm/backend/agents/
FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "shopfix"
SCENARIO_DIR = FIXTURE_ROOT / "scenarios"


@dataclass
class AgentAssignment:
    agent_id: str
    primary_file: str
    intent: str
    patch_path: Path | None = None


def _agent_id(index: int) -> str:
    return f"agent_{chr(ord('a') + index)}"


def load_assignments(suite: str, agent_count: int) -> list[AgentAssignment]:
    base = yaml.safe_load((SCENARIO_DIR / "base.yaml").read_text())
    cfg = yaml.safe_load((SCENARIO_DIR / f"{suite}.yaml").read_text())
    modules: dict = base["modules"]

    if suite == "disjoint":
        order = cfg["module_order"]
        assignments: list[AgentAssignment] = []
        for i in range(agent_count):
            mod_key = order[i % len(order)]
            mod = modules[mod_key]
            primary = mod["files"][0]
            intent = mod["intent_template"].format(feature=mod_key.replace("_", " "))
            patch = _patch_path(suite, agent_count, _agent_id(i))
            assignments.append(
                AgentAssignment(
                    agent_id=_agent_id(i),
                    primary_file=primary,
                    intent=intent,
                    patch_path=patch if patch.exists() else None,
                )
            )
        return assignments

    if suite == "contention":
        assignments = []
        clusters = cfg["clusters"]
        idx = 0
        for cluster in clusters:
            for intent in cluster["intents"]:
                if idx >= agent_count:
                    break
                aid = _agent_id(idx)
                patch = _patch_path(suite, agent_count, aid)
                assignments.append(
                    AgentAssignment(
                        agent_id=aid,
                        primary_file=cluster["file"],
                        intent=intent,
                        patch_path=patch if patch.exists() else None,
                    )
                )
                idx += 1
            if idx >= agent_count:
                break
        fill = cfg.get("fill_modules", [])
        fi = 0
        while idx < agent_count:
            mod_key = fill[fi % len(fill)]
            mod = modules[mod_key]
            primary = mod["files"][0]
            aid = _agent_id(idx)
            patch = _patch_path(suite, agent_count, aid)
            assignments.append(
                AgentAssignment(
                    agent_id=aid,
                    primary_file=primary,
                    intent=mod["intent_template"].format(feature=mod_key),
                    patch_path=patch if patch.exists() else None,
                )
            )
            idx += 1
            fi += 1
        return assignments

    raise ValueError(f"Unknown suite: {suite}")


def _patch_path(suite: str, agent_count: int, agent_id: str) -> Path:
    return FIXTURE_ROOT / "patches" / suite / f"n{agent_count}" / f"{agent_id}.patch"
