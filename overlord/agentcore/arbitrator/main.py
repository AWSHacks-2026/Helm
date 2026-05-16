"""
Overlord merge arbitrator — deployed to Amazon Bedrock AgentCore Runtime.

Invoke payload (JSON):
  {"agent_a": {"intent": str, "code": str}, "agent_b": {...}, "kb_context": optional}

Response: BedrockArbitrationResult JSON object.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from bedrock_agentcore import BedrockAgentCoreApp  # noqa: E402
from arbitration.runner import run_arbitration  # noqa: E402

app = BedrockAgentCoreApp()


@app.entrypoint
def handler(request: dict[str, Any]) -> dict[str, Any]:
    agent_a = request.get("agent_a") or {}
    agent_b = request.get("agent_b") or {}
    kb_context = request.get("kb_context")
    return run_arbitration(agent_a, agent_b, kb_context=kb_context)


if __name__ == "__main__":
    app.run()
