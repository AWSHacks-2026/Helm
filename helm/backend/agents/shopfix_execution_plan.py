"""Helm execution-plan helpers for ShopFix live benchmark (used by demo matrix)."""

from __future__ import annotations

import os
from collections import defaultdict

from agents.shopfix_scenarios import AgentAssignment, assignment_for_reassign, load_base_modules


def _reassign_enabled(suite: str) -> bool:
    if suite == "intent_opposition":
        return os.getenv("SHOPFIX_REASSIGN", "0") == "1"
    return os.getenv("SHOPFIX_REASSIGN", "1") != "0"


def _fused_coord_enabled(suite: str) -> bool:
    if suite != "intent_opposition":
        return False
    return os.getenv("SHOPFIX_FUSED_COORD", "1") != "0"


def _agents_by_file(assignments: list[AgentAssignment]) -> dict[str, list[AgentAssignment]]:
    by_file: dict[str, list[AgentAssignment]] = defaultdict(list)
    for item in assignments:
        by_file[item.primary_file].append(item)
    return dict(by_file)


def _disjoint_assignments(assignments: list[AgentAssignment]) -> list[AgentAssignment]:
    by_file = _agents_by_file(assignments)
    return [a for a in assignments if len(by_file.get(a.primary_file, [])) == 1]


def _trim_dedup_plan(
    assignments: list[AgentAssignment],
    *,
    continuations: list[str],
    reassignments: list[dict[str, str]],
    suite: str,
) -> tuple[list[str], list[dict[str, str]], list[str]]:
    cont = list(continuations)
    all_ids = {a.agent_id for a in assignments}
    reassign_by_id = {r["agent_id"]: r for r in reassignments}

    if not _reassign_enabled(suite):
        skipped = sorted(all_ids - set(cont))
        return cont, [], skipped

    by_file = _agents_by_file(assignments)
    reassign_out: list[dict[str, str]] = []
    skipped: list[str] = []

    for _fp, agents in by_file.items():
        if len(agents) < 2:
            continue
        losers = [a.agent_id for a in agents if a.agent_id not in cont]
        picked: str | None = None
        for aid in losers:
            if aid in reassign_by_id:
                reassign_out.append(reassign_by_id[aid])
                picked = aid
                break
        for aid in losers:
            if aid != picked:
                skipped.append(aid)

    return cont, reassign_out, sorted(set(skipped))


def _build_helm_execution_plan(
    suite: str,
    assignments: list[AgentAssignment],
    *,
    continuations: list[str],
    reassignments: list[dict[str, str]],
) -> tuple[dict[str, AgentAssignment], set[str], int]:
    by_id = {a.agent_id: a for a in assignments}
    modules = load_base_modules()
    reserved = {by_id[aid].primary_file for aid in continuations if aid in by_id}

    run_by_id: dict[str, AgentAssignment] = {}
    for aid in continuations:
        if aid in by_id:
            run_by_id[aid] = by_id[aid]

    reassign_ids: set[str] = set()
    for item in reassignments:
        aid = item["agent_id"]
        original = by_id.get(aid)
        if not original:
            continue
        mapped = assignment_for_reassign(
            original,
            item.get("suggested_new_task") or original.intent,
            suite=suite,
            modules=modules,
            reserved_files=reserved,
        )
        run_by_id[aid] = mapped
        reassign_ids.add(aid)
        reserved.add(mapped.primary_file)

    full_runs = sum(1 for aid in continuations if aid in by_id)
    return run_by_id, reassign_ids, full_runs
