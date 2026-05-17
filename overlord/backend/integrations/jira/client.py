from __future__ import annotations

import base64
import os
from typing import Any

import httpx


class JiraClient:
    def __init__(self, *, base_url: str, email: str, api_token: str, mock: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.mock = mock

    @classmethod
    def from_env(cls) -> JiraClient:
        return cls(
            base_url=os.getenv("JIRA_BASE_URL", "https://example.atlassian.net"),
            email=os.getenv("JIRA_EMAIL", ""),
            api_token=os.getenv("JIRA_API_TOKEN", ""),
            mock=os.getenv("JIRA_MOCK", "0") == "1",
        )

    def _auth_header(self) -> dict[str, str]:
        token = base64.b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        return {"Authorization": f"Basic {token}", "Accept": "application/json"}

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        if self.mock:
            return {
                "key": issue_key,
                "fields": {
                    "summary": f"Mock {issue_key}",
                    "description": "Work on src/auth/handlers.py",
                    "components": [{"name": "Auth"}],
                    "labels": ["overlord-ready"],
                },
            }
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, headers=self._auth_header())
            resp.raise_for_status()
            return resp.json()

    def add_comment(self, issue_key: str, body: str) -> None:
        if self.mock:
            return
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body}],
                    }
                ],
            }
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=self._auth_header(), json=payload)
            resp.raise_for_status()
