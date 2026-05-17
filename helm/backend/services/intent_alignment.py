from __future__ import annotations

import os
from typing import Any

from agents.simulator import resolve_intent_conflict
from bedrock.inference_routing import ComplexityInput, select_inference_tier


def maybe_align_on_declare(
    *,
    session_store: Any,
    session_id: str,
    agent_id: str,
    file_path: str,
    intent: str,
) -> dict[str, Any]:
    others = session_store.intents_on_file(session_id, file_path, exclude=agent_id)
    if not others:
        return {"overlap_detected": False, "alignment": None}

    agent_a = {"intent": others[0]["intent"], "code": ""}
    agent_b = {"intent": intent, "code": ""}
    tier = "haiku"

    if os.getenv("HELM_MOCK_BEDROCK") == "1":
        alignment = resolve_intent_conflict(agent_a, agent_b)
        alignment["inference_tier"] = "haiku"
    else:
        from bedrock import knowledge_base
        from helm import align_intents_tracked

        kb = knowledge_base.get_context_for_agents(
            [others[0]["agent_id"], agent_id],
            module_hint=file_path,
            session_id=session_id,
        )
        inp = ComplexityInput(
            operation="intent",
            agent_count=2,
            file_count=1,
            kb_event_count=len(kb or []),
            total_text_chars=len(agent_a["intent"]) + len(agent_b["intent"]),
            preflight_rule=None,
            has_substantive_code=False,
        )
        tier = select_inference_tier(inp)
        alignment = align_intents_tracked(
            agent_a,
            agent_b,
            kb_context=kb,
            tier=tier,
        )

    return {"overlap_detected": True, "alignment": alignment}
