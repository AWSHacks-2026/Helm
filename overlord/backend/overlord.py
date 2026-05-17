from __future__ import annotations

import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from arbitration.runner import run_arbitration
from bedrock.agentcore_client import invoke_arbitrator
from bedrock.invoke_tracked import invoke_anthropic_messages
from bedrock.model_ids import resolve_inference_profile_id
from models import BedrockArbitrationResult
from overlord_parse import extract_json_object
from bedrock.guardrail_routing import (
    escalate_sonnet_enabled,
    max_tokens_for_tier,
    model_id_for_tier,
    select_guardrail_tier,
    sonnet_min_agents,
)
from overlord_prompt import (
    build_guardrail_resolution_prompt,
    build_intent_conflict_prompt,
    build_merge_conflict_prompt,
    build_multi_agent_deduplication_prompt,
    build_multi_agent_guardrail_prompt,
    build_single_file_merge_prompt,
    build_task_deduplication_prompt,
)

OVERLORD_MODEL = resolve_inference_profile_id(
    os.getenv("OVERLORD_BEDROCK_MODEL_ID")
    or os.getenv("OVERLORD_BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-6")
)
MAX_TOKENS = 1500


def arbitrate(
    agent_a: dict,
    agent_b: dict,
    kb_context: str | list[dict[str, Any]] | None = None,
    conflict_kind: str = "merge",
    guardrail_context: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Resolve via AgentCore Runtime (merge + ARN), legacy runner, or tracked Bedrock."""
    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        if conflict_kind == "intent":
            return _mock_intent_resolution()
        if conflict_kind == "guardrail":
            return _mock_guardrail_resolution()
        return _mock_merge_resolution()

    arn = os.getenv("OVERLORD_ARBITRATOR_ARN", "").strip()
    if arn and conflict_kind == "merge":
        return invoke_arbitrator(
            agent_runtime_arn=arn,
            session_id=session_id or str(uuid.uuid4()),
            agent_a=agent_a,
            agent_b=agent_b,
            kb_context=kb_context,
        )

    if conflict_kind == "merge":
        return run_arbitration(agent_a, agent_b, kb_context=kb_context)

    if conflict_kind == "guardrail":
        fleet_agents = (guardrail_context or {}).get("fleet_agents")
        return resolve_guardrail(
            agent_a,
            agent_b,
            kb_context=kb_context,
            guardrail_context=guardrail_context,
            fleet_agents=fleet_agents,
        )

    return _arbitrate_tracked(
        agent_a,
        agent_b,
        kb_context=kb_context,
        conflict_kind=conflict_kind,
        guardrail_context=guardrail_context,
    )


def _agents_by_file(
    agents: dict[str, dict[str, Any]],
    file_paths: dict[str, str],
) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for agent_id, agent in agents.items():
        path = file_paths[agent_id]
        grouped.setdefault(path, {})[agent_id] = agent
    return grouped


def _fleet_merge_max_tokens() -> int:
    return int(os.getenv("MERGE_FLEET_MAX_TOKENS", os.getenv("LIVE_AGENT_MAX_TOKENS", "4096")))


def _fleet_parallel_enabled() -> bool:
    return os.getenv("MERGE_FLEET_PARALLEL", "1") == "1"


def _arbitrate_file_group(file_path: str, agents_on_file: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Merge all agents targeting one file (tracked Sonnet)."""
    if len(agents_on_file) == 1:
        only = next(iter(agents_on_file.values()))
        return {
            "file_path": file_path,
            "resolved_code": only["code"],
            "reasoning": "Single agent on file; no merge required.",
            "_usage": None,
        }

    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        return _mock_file_merge_resolution(file_path, agents_on_file)

    max_tokens = _fleet_merge_max_tokens()

    if len(agents_on_file) == 2:
        ids = sorted(agents_on_file.keys())
        prompt = build_merge_conflict_prompt(
            agents_on_file[ids[0]],
            agents_on_file[ids[1]],
        )
        text, usage = invoke_anthropic_messages(
            model_id=OVERLORD_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            role=f"overlord-merge-{file_path.replace('/', '-')}",
        )
        parsed = _parse_arbitration_response(text)
        return {
            "file_path": file_path,
            "resolved_code": parsed.get("resolved_code", ""),
            "reasoning": parsed.get("reasoning", ""),
            "_usage": {
                "model_id": usage.model_id,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "latency_ms": usage.latency_ms,
            },
        }

    prompt = build_single_file_merge_prompt(file_path, agents_on_file)
    text, usage = invoke_anthropic_messages(
        model_id=OVERLORD_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        role=f"overlord-merge-{file_path.replace('/', '-')}",
    )
    raw = extract_json_object(text)
    return {
        "file_path": file_path,
        "resolved_code": raw.get("resolved_code", ""),
        "reasoning": raw.get("reasoning", ""),
        "_usage": {
            "model_id": usage.model_id,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "latency_ms": usage.latency_ms,
        },
    }


def _mock_file_merge_resolution(
    file_path: str,
    agents_on_file: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    codes = [agent["code"] for agent in agents_on_file.values()]
    merged = codes[0]
    if len(codes) > 1:
        merged = (
            merged.rstrip()
            + "\n\n# MOCK fleet merge: combined intents\n"
            + "\n".join(f"# fragment {i + 1}" for i in range(1, len(codes)))
        )
    return {
        "file_path": file_path,
        "resolved_code": merged,
        "reasoning": f"MOCK: merged {len(codes)} agent variant(s) on {file_path}.",
        "_usage": None,
    }


def arbitrate_fleet(
    agents: dict[str, dict[str, Any]],
    file_paths: dict[str, str],
) -> dict[str, Any]:
    """Merge N agents across files — one Sonnet call per file (parallel by default)."""
    if len(agents) < 3:
        raise ValueError("arbitrate_fleet requires at least 3 agents")

    by_file = _agents_by_file(agents, file_paths)
    paths = sorted(by_file.keys())

    def merge_file(path: str) -> dict[str, Any]:
        return _arbitrate_file_group(path, by_file[path])

    file_results: list[dict[str, Any]] = []
    usages: list[dict[str, Any]] = []

    if _fleet_parallel_enabled() and len(paths) > 1:
        with ThreadPoolExecutor(max_workers=len(paths)) as pool:
            futures = {pool.submit(merge_file, path): path for path in paths}
            ordered: dict[str, dict[str, Any]] = {}
            for future in as_completed(futures):
                path = futures[future]
                item = future.result()
                ordered[path] = item
            file_results = [ordered[path] for path in paths]
    else:
        file_results = [merge_file(path) for path in paths]

    reasonings: list[str] = []
    for item in file_results:
        usage_meta = item.pop("_usage", None)
        if usage_meta:
            usages.append(usage_meta)
        if item.get("reasoning"):
            reasonings.append(f"{item['file_path']}: {item['reasoning']}")

    resolutions = [
        {"file_path": item["file_path"], "resolved_code": item["resolved_code"]}
        for item in file_results
    ]
    combined_usage = _combine_usage_records(usages)
    arbitration_calls = sum(1 for path in paths if len(by_file[path]) > 1)

    return {
        "conflict_type": "merge_conflict",
        "resolutions": resolutions,
        "reasoning": " ".join(reasonings),
        "tokens_saved_estimate": "~5000",
        "arbitration_calls": arbitration_calls,
        "parallel": _fleet_parallel_enabled(),
        "_usage": combined_usage,
    }


def _combine_usage_records(usages: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not usages:
        return None
    return {
        "model_id": usages[0]["model_id"],
        "input_tokens": sum(u["input_tokens"] for u in usages),
        "output_tokens": sum(u["output_tokens"] for u in usages),
        "latency_ms": max(u["latency_ms"] for u in usages),
    }


def _normalize_fleet_merge_resolution(
    raw: dict[str, Any],
    required_paths: list[str],
) -> dict[str, Any]:
    resolutions = raw.get("resolutions") or []
    if not isinstance(resolutions, list):
        raise ValueError("resolutions must be a list")

    by_path: dict[str, str] = {}
    for item in resolutions:
        path = item["file_path"]
        by_path[path] = item["resolved_code"]

    missing = [p for p in required_paths if p not in by_path]
    if missing:
        raise ValueError(f"fleet merge missing resolutions for: {missing}")

    return {
        "conflict_type": "merge_conflict",
        "resolutions": [
            {"file_path": path, "resolved_code": by_path[path]} for path in required_paths
        ],
        "reasoning": raw.get("reasoning", ""),
        "tokens_saved_estimate": raw.get("tokens_saved_estimate", "~5000"),
    }


def _mock_fleet_merge_resolution(
    agents: dict[str, dict[str, Any]],
    file_paths: dict[str, str],
) -> dict[str, Any]:
    paths = sorted(set(file_paths.values()))
    resolutions: list[dict[str, str]] = []
    for path in paths:
        on_file = [agents[aid]["code"] for aid, fp in file_paths.items() if fp == path]
        merged = on_file[0]
        if len(on_file) > 1:
            merged = (
                merged.rstrip()
                + "\n\n# MOCK fleet merge: combined intents\n"
                + "\n".join(f"# fragment from variant {i + 1}" for i in range(1, len(on_file)))
            )
        resolutions.append({"file_path": path, "resolved_code": merged})
    return {
        "conflict_type": "merge_conflict",
        "resolutions": resolutions,
        "reasoning": (
            "MOCK: Merged each file's agent variants into one module per path."
        ),
        "tokens_saved_estimate": "~5000 (mock)",
    }


def _append_kb_context(
    prompt: str,
    kb_context: str | list[dict[str, Any]] | None,
) -> str:
    if not kb_context:
        return prompt
    kb_text = (
        json.dumps(kb_context, indent=2)
        if isinstance(kb_context, list)
        else kb_context
    )
    return f"{prompt}\n\nRelevant history from Knowledge Base:\n{kb_text}"


def _guardrail_usage_meta(usage: Any, tier: str, escalated: bool) -> dict[str, Any]:
    return {
        "model_id": usage.model_id,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "latency_ms": usage.latency_ms,
        "resolution_tier": tier,
        "escalated_to_sonnet": escalated,
    }


def _needs_guardrail_escalation(result: dict[str, Any]) -> bool:
    if not result.get("reasoning"):
        return True
    verdict = (result.get("verdict") or "").strip().lower()
    return verdict not in {"modify", "block", "allow_with_changes"}


def _invoke_guardrail_prompt(
    prompt: str,
    *,
    tier: str,
    role: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    model_id = model_id_for_tier(tier)
    text, usage = invoke_anthropic_messages(
        model_id=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens_for_tier(tier),
        role=role,
    )
    try:
        result = _parse_arbitration_response(text)
    except Exception:
        raw = extract_json_object(text)
        result = dict(raw)
        if "verdict" in raw:
            result["verdict"] = raw["verdict"]
    return result, _guardrail_usage_meta(usage, tier, False)


def resolve_guardrail(
    agent_a: dict,
    agent_b: dict,
    *,
    kb_context: str | list[dict[str, Any]] | None = None,
    guardrail_context: dict[str, Any] | None = None,
    fleet_agents: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Tiered guardrail resolution: Haiku for simple pairwise, Sonnet for fleet/complex."""
    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        result = _mock_guardrail_resolution()
        agents = fleet_agents if fleet_agents and len(fleet_agents) >= sonnet_min_agents() else None
        result["resolution_tier"] = "sonnet" if agents else "haiku"
        result["escalated_to_sonnet"] = False
        return result

    ctx = guardrail_context or {}
    proposed = ctx.get("proposed_action") or {}
    rule = str(ctx.get("rule", ""))
    message = str(ctx.get("message", ""))
    kb_list = kb_context if isinstance(kb_context, list) else None

    if fleet_agents and len(fleet_agents) >= sonnet_min_agents():
        tier = "sonnet"
        prompt = build_multi_agent_guardrail_prompt(
            fleet_agents,
            proposed,
            rule=rule,
            message=message,
        )
        prompt = _append_kb_context(prompt, kb_context)
        result, usage_meta = _invoke_guardrail_prompt(
            prompt,
            tier=tier,
            role="overlord-guardrail-fleet",
        )
        usage_meta["agent_count"] = len(fleet_agents)
        result["_usage"] = usage_meta
        result["resolution_tier"] = tier
        result["escalated_to_sonnet"] = False
        return result

    tier = select_guardrail_tier(
        agent_count=2,
        preflight_rule=rule or None,
        kb_context=kb_list,
        proposed_action=proposed,
    )
    prompt = build_guardrail_resolution_prompt(
        agent_a,
        agent_b,
        proposed_action=proposed,
        rule=rule,
        message=message,
    )
    prompt = _append_kb_context(prompt, kb_context)
    result, usage_meta = _invoke_guardrail_prompt(
        prompt,
        tier=tier,
        role=f"overlord-guardrail-{tier}",
    )
    escalated = False

    if tier == "haiku" and escalate_sonnet_enabled() and _needs_guardrail_escalation(result):
        sonnet_prompt = prompt
        sonnet_result, sonnet_usage = _invoke_guardrail_prompt(
            sonnet_prompt,
            tier="sonnet",
            role="overlord-guardrail-sonnet-escalation",
        )
        sonnet_usage["escalated_to_sonnet"] = True
        sonnet_usage["resolution_tier"] = "sonnet"
        sonnet_result["_usage"] = sonnet_usage
        sonnet_result["resolution_tier"] = "sonnet"
        sonnet_result["escalated_to_sonnet"] = True
        return sonnet_result

    usage_meta["agent_count"] = 2
    result["_usage"] = usage_meta
    result["resolution_tier"] = tier
    result["escalated_to_sonnet"] = escalated
    return result


def _arbitrate_tracked(
    agent_a: dict,
    agent_b: dict,
    *,
    kb_context: str | list[dict[str, Any]] | None,
    conflict_kind: str,
    guardrail_context: dict[str, Any] | None,
) -> dict[str, Any]:
    prompt = _build_prompt(agent_a, agent_b, conflict_kind, guardrail_context)
    prompt = _append_kb_context(prompt, kb_context)

    text, usage = invoke_anthropic_messages(
        model_id=OVERLORD_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=MAX_TOKENS,
        role="overlord",
    )
    result = _parse_arbitration_response(text)
    result["_usage"] = {
        "model_id": usage.model_id,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "latency_ms": usage.latency_ms,
    }
    return result


def _build_prompt(
    agent_a: dict,
    agent_b: dict,
    conflict_kind: str,
    guardrail_context: dict[str, Any] | None,
) -> str:
    if conflict_kind == "intent":
        return build_intent_conflict_prompt(agent_a, agent_b)
    if conflict_kind == "guardrail":
        ctx = guardrail_context or {}
        return build_guardrail_resolution_prompt(
            agent_a,
            agent_b,
            proposed_action=ctx.get("proposed_action", {}),
            rule=ctx.get("rule", ""),
            message=ctx.get("message", ""),
        )
    return build_merge_conflict_prompt(agent_a, agent_b)


def _parse_arbitration_response(text: str) -> dict[str, Any]:
    raw = extract_json_object(text)
    validated = BedrockArbitrationResult.model_validate(raw)
    result = validated.model_dump()
    if "verdict" in raw:
        result["verdict"] = raw["verdict"]
    return result


def detect_duplication(agent_a: dict, agent_b: dict) -> dict[str, Any]:
    """Call Sonnet via Bedrock to detect duplicate semantic work between agents."""
    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        return _mock_duplication_resolution()

    prompt = build_task_deduplication_prompt(agent_a, agent_b)
    text, usage = invoke_anthropic_messages(
        model_id=OVERLORD_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        role="overlord-dedup",
    )
    raw = extract_json_object(text)
    result = _normalize_duplication_resolution(raw)
    result["_usage"] = {
        "model_id": usage.model_id,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "latency_ms": usage.latency_ms,
    }
    return result


def detect_duplication_fleet(agents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """One Sonnet call to deduplicate N agents (3+)."""
    if len(agents) < 3:
        raise ValueError("detect_duplication_fleet requires at least 3 agents")

    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        return _mock_fleet_duplication_resolution(agents)

    prompt = build_multi_agent_deduplication_prompt(agents)
    text, usage = invoke_anthropic_messages(
        model_id=OVERLORD_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        role="overlord-dedup-fleet",
    )
    raw = extract_json_object(text)
    result = _normalize_fleet_duplication_resolution(raw, set(agents))
    result["_usage"] = {
        "model_id": usage.model_id,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "latency_ms": usage.latency_ms,
    }
    return result


def _normalize_duplication_resolution(raw: dict[str, Any]) -> dict[str, Any]:
    duplicate_detected = raw["duplicate_detected"]
    if not isinstance(duplicate_detected, bool):
        raise ValueError("duplicate_detected must be a boolean")

    agent_to_continue = raw["agent_to_continue"]
    agent_to_reassign = raw["agent_to_reassign"]
    valid_agents = {"agent_a", "agent_b"}
    if agent_to_continue not in valid_agents or agent_to_reassign not in valid_agents:
        raise ValueError("agent assignments must be agent_a or agent_b")
    if agent_to_continue == agent_to_reassign:
        raise ValueError("agent_to_continue and agent_to_reassign must differ")

    return {
        "conflict_type": "duplicate_work",
        "duplicate_detected": duplicate_detected,
        "agent_to_continue": agent_to_continue,
        "agent_to_reassign": agent_to_reassign,
        "suggested_new_task": raw["suggested_new_task"],
        "reasoning": raw["reasoning"],
        "resolved_code": "",
        "tokens_saved_estimate": raw.get("tokens_saved_estimate", "~1800"),
    }


def _normalize_fleet_duplication_resolution(
    raw: dict[str, Any],
    valid_agents: set[str],
) -> dict[str, Any]:
    duplicate_detected = raw["duplicate_detected"]
    if not isinstance(duplicate_detected, bool):
        raise ValueError("duplicate_detected must be a boolean")

    continuations = raw.get("continuations") or []
    reassignments = raw.get("reassignments") or []
    if not isinstance(continuations, list) or not isinstance(reassignments, list):
        raise ValueError("continuations and reassignments must be lists")

    seen: set[str] = set()
    for agent_id in continuations:
        if agent_id not in valid_agents:
            raise ValueError(f"unknown continuation agent: {agent_id}")
        if agent_id in seen:
            raise ValueError(f"duplicate assignment for {agent_id}")
        seen.add(agent_id)

    normalized_reassignments: list[dict[str, str]] = []
    for item in reassignments:
        agent_id = item["agent_id"]
        if agent_id not in valid_agents:
            raise ValueError(f"unknown reassignment agent: {agent_id}")
        if agent_id in seen:
            raise ValueError(f"duplicate assignment for {agent_id}")
        seen.add(agent_id)
        normalized_reassignments.append(
            {
                "agent_id": agent_id,
                "suggested_new_task": item["suggested_new_task"],
            }
        )

    if seen != valid_agents:
        missing = valid_agents - seen
        extra = seen - valid_agents
        raise ValueError(
            f"fleet assignments must cover all agents; missing={missing} extra={extra}"
        )

    return {
        "conflict_type": "duplicate_work",
        "duplicate_detected": duplicate_detected,
        "continuations": list(continuations),
        "reassignments": normalized_reassignments,
        "reasoning": raw["reasoning"],
        "resolved_code": "",
        "tokens_saved_estimate": raw.get("tokens_saved_estimate", "~1800"),
    }


def _mock_merge_resolution() -> dict[str, Any]:
    return {
        "conflict_type": "merge_conflict",
        "reasoning": "MOCK: Combined Agent A caching with Agent B type hints.",
        "resolved_code": (
            "def get_user(user_id: str) -> User:\n"
            "    if user_id in cache:\n"
            "        return cache[user_id]\n"
            "    result = db.query(user_id)\n"
            "    cache[user_id] = result\n"
            "    return result\n"
        ),
        "tokens_saved_estimate": "~2400 (mock)",
    }


def _mock_intent_resolution() -> dict[str, Any]:
    return {
        "conflict_type": "intent_conflict",
        "compatibility": "conflict",
        "unified_intent": (
            "Optimize for performance where measurable, but prefer native Python "
            "implementations unless a dependency saves at least 20% latency."
        ),
        "priority_order": [
            "preserve deployability and low dependency count",
            "improve latency with standard-library techniques first",
        ],
        "agent_updates": {
            "agent_a": "Benchmark stdlib json plus functools.lru_cache before proposing orjson.",
            "agent_b": "Keep dependency removals unless benchmark evidence supports an exception.",
        },
        "reasoning": (
            "MOCK: Agent A optimizes for performance (cache + pooling) while Agent B "
            "minimizes dependencies. Compromise: use stdlib sqlite with a small "
            "in-process LRU cache — no third-party pool."
        ),
        "resolved_code": (
            "Unified directive: Prefer native sqlite3 access with an optional "
            "functools.lru_cache on get_user(); avoid new pip dependencies."
        ),
        "tokens_saved_estimate": "~1800 (mock)",
    }


def _mock_guardrail_resolution(*, tier: str = "haiku") -> dict[str, Any]:
    return {
        "conflict_type": "proactive_guardrail",
        "reasoning": "MOCK: Agent B must not delete utils/cache.py; Agent A invested in caching.",
        "resolved_code": (
            "# Refactor around utils/cache.py: slim the public API instead of deleting."
        ),
        "tokens_saved_estimate": "~2400 (mock)",
        "verdict": "modify",
        "resolution_tier": tier,
        "escalated_to_sonnet": False,
    }


def _mock_duplication_resolution() -> dict[str, Any]:
    return {
        "conflict_type": "duplicate_work",
        "duplicate_detected": True,
        "agent_to_continue": "agent_a",
        "agent_to_reassign": "agent_b",
        "suggested_new_task": "Implement audit logging for authentication events.",
        "reasoning": (
            "Both agents are working on overlapping user authentication tasks; "
            "Agent A should continue because its scope covers the login flow, while "
            "Agent B should move to adjacent audit logging work."
        ),
        "resolved_code": "",
        "tokens_saved_estimate": "~1800 (mock)",
    }


def _mock_fleet_duplication_resolution(
    agents: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(agents.keys())
    continuations = [ordered[0]]
    if len(ordered) >= 4:
        continuations.append(ordered[3])
    if len(ordered) >= 6:
        continuations.append(ordered[5])

    continuation_set = set(continuations)
    reassignments: list[dict[str, str]] = []
    tasks = [
        "Implement audit logging for authentication events.",
        "Add rate limiting middleware on login routes.",
        "Build product recommendation scoring (non-search).",
        "Add webhook notifications for invoice state changes.",
        "Implement admin dashboard metrics export.",
    ]
    task_idx = 0
    for agent_id in ordered:
        if agent_id in continuation_set:
            continue
        reassignments.append(
            {
                "agent_id": agent_id,
                "suggested_new_task": tasks[task_idx % len(tasks)],
            }
        )
        task_idx += 1

    return {
        "conflict_type": "duplicate_work",
        "duplicate_detected": True,
        "continuations": continuations,
        "reassignments": reassignments,
        "reasoning": (
            "MOCK: Clustered overlapping auth and catalog agents; one continuation per "
            "cluster, others reassigned to adjacent non-overlapping tasks."
        ),
        "resolved_code": "",
        "tokens_saved_estimate": "~1800 (mock)",
    }
