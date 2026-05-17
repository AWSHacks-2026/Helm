from __future__ import annotations

import os
import re


def resolve_agent_id() -> str:
    raw = os.getenv("OVERLORD_AGENT_ID", "").strip()
    if not raw:
        return "agent_local"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw)[:64]
    return slug or "agent_local"
