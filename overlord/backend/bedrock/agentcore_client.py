from __future__ import annotations

import json
import os
from typing import Any

import boto3
from dotenv import load_dotenv

from models import BedrockArbitrationResult
from overlord_parse import extract_json_object

load_dotenv()

REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")


def get_agentcore_client():
    return boto3.client("bedrock-agentcore", region_name=REGION)


def parse_agentcore_response(response: dict[str, Any]) -> dict[str, Any]:
    """Decode InvokeAgentRuntime response (JSON or event-stream) into arbitration dict."""
    content_type = response.get("contentType", "")

    if content_type == "application/json":
        parts = []
        for chunk in response.get("response", []):
            parts.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk))
        data = json.loads("".join(parts))
        if isinstance(data, dict) and "conflict_type" in data:
            return BedrockArbitrationResult.model_validate(data).model_dump()
        if isinstance(data, dict) and "result" in data:
            inner = data["result"]
            if isinstance(inner, str):
                return BedrockArbitrationResult.model_validate(
                    extract_json_object(inner)
                ).model_dump()
            return BedrockArbitrationResult.model_validate(inner).model_dump()
        return BedrockArbitrationResult.model_validate(data).model_dump()

    if "text/event-stream" in content_type:
        lines: list[str] = []
        stream = response.get("response")
        if stream is not None and hasattr(stream, "iter_lines"):
            for line in stream.iter_lines(chunk_size=10):
                if not line:
                    continue
                decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                if decoded.startswith("data: "):
                    lines.append(decoded[6:])
        combined = "\n".join(lines)
        return BedrockArbitrationResult.model_validate(
            extract_json_object(combined)
        ).model_dump()

    raise ValueError(f"Unsupported AgentCore response contentType: {content_type!r}")


def invoke_arbitrator(
    agent_runtime_arn: str,
    session_id: str,
    agent_a: dict,
    agent_b: dict,
    kb_context: str | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    client = get_agentcore_client()
    payload_dict: dict[str, Any] = {
        "agent_a": agent_a,
        "agent_b": agent_b,
    }
    if kb_context is not None:
        payload_dict["kb_context"] = kb_context

    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps(payload_dict).encode("utf-8"),
    )
    return parse_agentcore_response(response)
