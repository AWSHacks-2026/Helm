from __future__ import annotations

import os
import uuid
from typing import Any

from arbitration.runner import run_arbitration
from bedrock.agentcore_client import invoke_arbitrator


def arbitrate(
    agent_a: dict,
    agent_b: dict,
    kb_context: str | list[dict[str, Any]] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        return _mock_merge_resolution()

    arn = os.getenv("OVERLORD_ARBITRATOR_ARN", "").strip()
    if arn:
        return invoke_arbitrator(
            agent_runtime_arn=arn,
            session_id=session_id or str(uuid.uuid4()),
            agent_a=agent_a,
            agent_b=agent_b,
            kb_context=kb_context,
        )

    return run_arbitration(agent_a, agent_b, kb_context=kb_context)


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
