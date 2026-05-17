from __future__ import annotations

import os
from typing import Any

import httpx


class GitHubClient:
    def __init__(
        self,
        *,
        token: str,
        repo: str,
        mock: bool = False,
        api_base: str = "https://api.github.com",
    ) -> None:
        self.token = token
        self.repo = repo
        self.mock = mock
        self.api_base = api_base.rstrip("/")
        if "/" not in repo:
            raise ValueError("GITHUB_REPO must be owner/name")

    @classmethod
    def from_env(cls) -> GitHubClient:
        return cls(
            token=os.getenv("GITHUB_TOKEN", ""),
            repo=os.getenv("GITHUB_REPO", "mergeai/default"),
            mock=os.getenv("GITHUB_MOCK", "0") == "1",
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        if self.mock:
            return {
                "number": issue_number,
                "title": f"Mock issue {issue_number}",
                "body": "Work on src/auth/handlers.py",
                "labels": [{"name": "auth"}, {"name": "helm-ready"}],
            }
        owner, name = self.repo.split("/", 1)
        url = f"{self.api_base}/repos/{owner}/{name}/issues/{issue_number}"
        with httpx.Client(timeout=30.0) as http:
            resp = http.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def add_comment(self, issue_number: int, body: str) -> None:
        if self.mock:
            return
        owner, name = self.repo.split("/", 1)
        url = f"{self.api_base}/repos/{owner}/{name}/issues/{issue_number}/comments"
        with httpx.Client(timeout=30.0) as http:
            resp = http.post(url, headers=self._headers(), json={"body": body})
            resp.raise_for_status()

    def parse_external_id(self, external_id: str) -> int:
        if "#" not in external_id:
            raise ValueError(f"invalid github external_id: {external_id}")
        return int(external_id.rsplit("#", 1)[-1])
