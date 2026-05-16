from __future__ import annotations

import os
import re

from bedrock.invoke_tracked import InvokeUsage, invoke_anthropic_messages
from bedrock.model_ids import resolve_inference_profile_id

_DEFAULT_AGENT_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
_LEGACY_HAIKU = "claude-3-5-haiku"


def agent_model_id() -> str:
    raw = os.getenv("OVERLORD_AGENT_MODEL_ID", _DEFAULT_AGENT_MODEL)
    resolved = resolve_inference_profile_id(raw)
    if _LEGACY_HAIKU in raw:
        return resolve_inference_profile_id(_DEFAULT_AGENT_MODEL)
    return resolved


MAX_TOKENS = int(os.getenv("LIVE_AGENT_MAX_TOKENS", "800"))


def build_initial_edit_prompt(
    *,
    agent_id: str,
    file_path: str,
    intent: str,
    peer_code: str | None,
) -> str:
    peer_block = ""
    if peer_code:
        peer_block = f"\nThe other agent already wrote:\n```\n{peer_code}\n```\n"
    return (
        f"You are {agent_id}, an AI coding agent editing `{file_path}`.\n"
        f"Your intent: {intent}\n"
        f"{peer_block}"
        "Output ONLY valid Python for this file section (no markdown fences, no explanation)."
    )


def build_merge_fix_prompt(
    *,
    agent_id: str,
    file_path: str,
    intent: str,
    own_code: str,
    peer_code: str,
) -> str:
    return (
        f"You are {agent_id} fixing a merge conflict in `{file_path}`.\n"
        f"Your intent: {intent}\n\n"
        f"Your last version:\n```\n{own_code}\n```\n\n"
        f"The other agent's version:\n```\n{peer_code}\n```\n\n"
        "Produce ONE merged Python implementation that satisfies your intent where possible. "
        "Do NOT leave git conflict markers. Output ONLY code."
    )


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def run_agent_edit(
    *,
    agent_id: str,
    file_path: str,
    intent: str,
    peer_code: str | None,
) -> tuple[str, InvokeUsage]:
    prompt = build_initial_edit_prompt(
        agent_id=agent_id,
        file_path=file_path,
        intent=intent,
        peer_code=peer_code,
    )
    text, usage = invoke_anthropic_messages(
        model_id=agent_model_id(),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=MAX_TOKENS,
        role=agent_id,
    )
    return _strip_fences(text), usage


def run_agent_merge_fix(
    *,
    agent_id: str,
    file_path: str,
    intent: str,
    own_code: str,
    peer_code: str,
) -> tuple[str, InvokeUsage]:
    prompt = build_merge_fix_prompt(
        agent_id=agent_id,
        file_path=file_path,
        intent=intent,
        own_code=own_code,
        peer_code=peer_code,
    )
    text, usage = invoke_anthropic_messages(
        model_id=agent_model_id(),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=MAX_TOKENS,
        role=agent_id,
    )
    return _strip_fences(text), usage
