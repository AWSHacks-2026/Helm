from __future__ import annotations

from dataclasses import dataclass, field

import httpx


@dataclass
class HelmClient:
    base_url: str
    session_id: str
    api_calls: int = 0
    intents_posted: int = 0
    guardrails_checked: int = 0
    guardrails_blocked: int = 0
    _client: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.Client(base_url=self.base_url, timeout=60.0)

    def close(self) -> None:
        self._client.close()

    def declare_intent(self, agent_id: str, file_path: str, intent: str) -> dict:
        self.api_calls += 1
        self.intents_posted += 1
        response = self._client.post(
            "/intents",
            json={
                "session_id": self.session_id,
                "agent_id": agent_id,
                "file_path": file_path,
                "intent": intent,
            },
        )
        response.raise_for_status()
        return response.json()

    def guardrail_check(
        self,
        agent_id: str,
        file_path: str,
        proposed_code: str,
    ) -> dict:
        self.api_calls += 1
        self.guardrails_checked += 1
        response = self._client.post(
            "/guardrails/check",
            json={
                "session_id": self.session_id,
                "agent_id": agent_id,
                "file_path": file_path,
                "action": "write",
                "proposed_code": proposed_code,
            },
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("allowed", True):
            self.guardrails_blocked += 1
        return data

    def stats(self) -> dict:
        return {
            "api_calls": self.api_calls,
            "intents_posted": self.intents_posted,
            "guardrails_checked": self.guardrails_checked,
            "guardrails_blocked": self.guardrails_blocked,
        }
