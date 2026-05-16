from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Awaitable, Callable

SendFn = Callable[[str], Awaitable[None]]


class ConnectionManager:
    def __init__(self) -> None:
        self._subs: dict[str, list[SendFn]] = defaultdict(list)

    def subscribe(self, session_id: str, send: SendFn) -> None:
        self._subs[session_id].append(send)

    def unsubscribe(self, session_id: str, send: SendFn) -> None:
        self._subs[session_id] = [s for s in self._subs[session_id] if s is not send]

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        payload = json.dumps(message, default=str)
        for send in list(self._subs.get(session_id, [])):
            await send(payload)
