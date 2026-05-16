from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sessions"


def _session_path(session_id: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{session_id}.json"


def append_event(session_id: str, event: dict[str, Any]) -> dict[str, Any]:
    path = _session_path(session_id)
    events: list[dict[str, Any]] = []
    if path.exists():
        events = json.loads(path.read_text())
    record = {
        "event_id": str(uuid.uuid4()),
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    events.append(record)
    path.write_text(json.dumps(events, indent=2))
    return record


def list_history(session_id: str) -> list[dict[str, Any]]:
    path = _session_path(session_id)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = json.loads(path.read_text())
    return sorted(events, key=lambda item: item.get("timestamp", ""), reverse=True)


def get_context_for_agents(agent_ids: list[str], module_hint: str = "") -> str:
    if not DATA_DIR.exists():
        return ""

    lines: list[str] = []
    for path in sorted(DATA_DIR.glob("*.json")):
        events = json.loads(path.read_text())
        for event in events[-10:]:
            payload = event.get("payload", event)
            agent_id = payload.get("agent_id", "")
            file_path = payload.get("file_path", "")
            if agent_id in agent_ids or (module_hint and module_hint in file_path):
                lines.append(json.dumps(event))
    return "\n".join(lines[-10:])
