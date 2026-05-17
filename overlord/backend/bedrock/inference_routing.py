from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from agents.haiku_agent import agent_model_id
from bedrock.model_ids import resolve_inference_profile_id

Operation = Literal["guardrail", "intent", "dedup", "merge"]
Tier = Literal["haiku", "sonnet"]


@dataclass(frozen=True)
class ComplexityInput:
    operation: Operation
    agent_count: int
    file_count: int
    kb_event_count: int
    total_text_chars: int
    preflight_rule: str | None
    has_substantive_code: bool


def _strategy_override() -> str | None:
    raw = os.getenv("OVERLORD_INFERENCE_STRATEGY", "").strip().lower()
    if raw in {"haiku", "sonnet"}:
        return raw
    legacy = os.getenv("GUARDRAIL_STRATEGY", "").strip().lower()
    if legacy in {"haiku", "sonnet"}:
        return legacy
    return None


def compute_complexity_score(inp: ComplexityInput) -> int:
    score = 0
    op_weight = {"guardrail": 10, "intent": 15, "dedup": 20, "merge": 25}
    score += op_weight.get(inp.operation, 15)
    score += max(0, inp.agent_count - 2) * 12
    score += max(0, inp.file_count - 1) * 8
    score += min(inp.kb_event_count, 20) * 2
    score += min(inp.total_text_chars // 500, 20)
    if inp.preflight_rule in {"intent_contradiction"}:
        score += 25
    if inp.has_substantive_code:
        score += 15
    return score


def sonnet_threshold() -> int:
    return int(os.getenv("OVERLORD_SONNET_COMPLEXITY_THRESHOLD", "45"))


def sonnet_min_agents() -> int:
    return int(os.getenv("GUARDRAIL_SONNET_MIN_AGENTS", "3"))


def select_inference_tier(inp: ComplexityInput) -> Tier:
    override = _strategy_override()
    if override:
        return override  # type: ignore[return-value]
    if inp.agent_count >= sonnet_min_agents():
        return "sonnet"
    return "sonnet" if compute_complexity_score(inp) >= sonnet_threshold() else "haiku"


def sonnet_model_id() -> str:
    return resolve_inference_profile_id(
        os.getenv("OVERLORD_BEDROCK_MODEL_ID")
        or os.getenv("OVERLORD_BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-6")
    )


def haiku_max_tokens() -> int:
    return int(os.getenv("GUARDRAIL_HAIKU_MAX_TOKENS", "1024"))


def sonnet_max_tokens() -> int:
    return int(os.getenv("GUARDRAIL_SONNET_MAX_TOKENS", "1500"))


def model_id_for_tier(tier: str) -> str:
    if tier == "haiku":
        return agent_model_id()
    return sonnet_model_id()


def max_tokens_for_tier(tier: str) -> int:
    if tier == "haiku":
        return haiku_max_tokens()
    return sonnet_max_tokens()
