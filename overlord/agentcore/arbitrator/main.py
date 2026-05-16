"""
Overlord merge arbitrator — Amazon Bedrock AgentCore Runtime entrypoint.

Invoke payload (JSON):
  {"agent_a": {"intent": str, "code": str}, "agent_b": {...}, "kb_context": optional}
"""

from __future__ import annotations

from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp

from runtime_logic import parse_invoke_request, run_arbitration

app = BedrockAgentCoreApp()


@app.entrypoint
def handler(request: dict[str, Any]) -> dict[str, Any]:
    try:
        agent_a, agent_b, kb_context = parse_invoke_request(request)
    except ValueError as exc:
        return {"error": str(exc), "conflict_type": "error"}
    return run_arbitration(agent_a, agent_b, kb_context=kb_context)


if __name__ == "__main__":
    app.run()
