from __future__ import annotations

from models import GuardrailCheckResponse
from store.sessions import SessionStore


def check_action(
    *,
    session_id: str,
    agent_id: str,
    file_path: str,
    action: str,
    proposed_code: str,
    session_store: SessionStore,
) -> GuardrailCheckResponse:
    del proposed_code  # reserved for semantic checks later

    others = session_store.agents_on_file(session_id, file_path, exclude=agent_id)
    if action in {"write", "delete"} and others:
        return GuardrailCheckResponse(
            allowed=False,
            reason=f"File {file_path} active for agents: {', '.join(others)}",
            route_to_overlord=True,
        )
    return GuardrailCheckResponse(allowed=True)
