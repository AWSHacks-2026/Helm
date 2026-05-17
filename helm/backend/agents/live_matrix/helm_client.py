from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx


def _retry_after_sec(response: httpx.Response, attempt: int) -> float:
    raw = response.headers.get("retry-after")
    if raw:
        try:
            return max(1.0, float(raw))
        except ValueError:
            pass
    return min(60.0, 2.0 * (2**attempt))


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
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=120.0,
            headers={"X-Helm-Live-Matrix": "1"},
        )

    def close(self) -> None:
        self._client.close()

    def _post_with_retry(self, path: str, payload: dict) -> httpx.Response:
        last: httpx.Response | None = None
        for attempt in range(6):
            response = self._client.post(path, json=payload)
            last = response
            if response.status_code < 500:
                return response
            time.sleep(_retry_after_sec(response, attempt))
        assert last is not None
        return last

    def declare_intent(self, agent_id: str, file_path: str, intent: str) -> dict:
        self.api_calls += 1
        self.intents_posted += 1
        response = self._post_with_retry(
            "/intents",
            {
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
        response = self._post_with_retry(
            "/guardrails/check",
            {
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
