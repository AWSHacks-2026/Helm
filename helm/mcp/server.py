"""Helm MCP server — exposes supervisor tools to Cursor / Claude Code."""

from __future__ import annotations

import os

import httpx

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    raise SystemExit("Install mcp: pip install mcp") from None

BASE = os.getenv("HELM_API_BASE", "http://127.0.0.1:8000")
mcp = FastMCP("helm")


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=60.0)


@mcp.tool()
def helm_declare_intent(
    session_id: str, agent_id: str, file_path: str, intent: str
) -> dict:
    """Record an agent's declared intent before editing a file."""
    with _client() as client:
        response = client.post(
            "/intents",
            json={
                "session_id": session_id,
                "agent_id": agent_id,
                "file_path": file_path,
                "intent": intent,
            },
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
def helm_guardrail_check(
    session_id: str,
    agent_id: str,
    file_path: str,
    action: str,
    proposed_code: str = "",
) -> dict:
    """Pre-flight check before an agent writes to a file.

    When blocked due to file overlap, the response includes a ``handoff`` object
    with owner intent and optional backlog mission suggestion.
    """
    with _client() as client:
        response = client.post(
            "/guardrails/check",
            json={
                "session_id": session_id,
                "agent_id": agent_id,
                "file_path": file_path,
                "action": action,
                "proposed_code": proposed_code,
            },
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
def helm_resolve_conflict(
    session_id: str,
    file_path: str,
    agent_a_id: str,
    agent_a_intent: str,
    agent_a_code: str,
    agent_b_id: str,
    agent_b_intent: str,
    agent_b_code: str,
) -> dict:
    """Arbitrate a merge conflict between two agents via Bedrock Sonnet."""
    with _client() as client:
        response = client.post(
            "/resolve",
            json={
                "session_id": session_id,
                "file_path": file_path,
                "agent_a": {
                    "agent_id": agent_a_id,
                    "intent": agent_a_intent,
                    "code": agent_a_code,
                },
                "agent_b": {
                    "agent_id": agent_b_id,
                    "intent": agent_b_intent,
                    "code": agent_b_code,
                },
            },
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
def helm_get_history(session_id: str) -> list:
    """Fetch session event history (intents, blocks, resolutions)."""
    with _client() as client:
        response = client.get("/history", params={"session_id": session_id})
        response.raise_for_status()
        return response.json()


@mcp.tool()
def helm_record_checkpoint(
    session_id: str,
    agent_id: str,
    event: str,
    detail: str = "",
) -> dict:
    """Record agent lifecycle events (started, committed, merge_conflict) for benchmarks."""
    with _client() as client:
        response = client.post(
            "/history/checkpoint",
            json={
                "session_id": session_id,
                "agent_id": agent_id,
                "event": event,
                "detail": detail,
            },
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run()
