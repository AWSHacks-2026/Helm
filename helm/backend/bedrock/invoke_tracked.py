from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

from bedrock.client import get_bedrock_client
from bedrock.model_ids import resolve_inference_profile_id


@dataclass(frozen=True)
class InvokeUsage:
    model_id: str
    role: str
    input_tokens: int
    output_tokens: int
    latency_ms: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def _mock_enabled() -> bool:
    return os.getenv("HELM_MOCK_BEDROCK") == "1"


def invoke_anthropic_messages(
    *,
    model_id: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    role: str,
) -> tuple[str, InvokeUsage]:
    started = time.perf_counter()
    if _mock_enabled():
        text = messages[-1]["content"][:200]
        usage = InvokeUsage(
            model_id=model_id,
            role=role,
            input_tokens=len(json.dumps(messages)) // 4,
            output_tokens=len(text) // 4,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return f"# MOCK({role})\n{text}", usage

    resolved_id = resolve_inference_profile_id(model_id)
    client = get_bedrock_client()
    response = client.invoke_model(
        modelId=resolved_id,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": messages,
            }
        ),
    )
    payload = json.loads(response["body"].read())
    text = payload["content"][0]["text"]
    raw_usage = payload.get("usage") or {}
    usage = InvokeUsage(
        model_id=resolved_id,
        role=role,
        input_tokens=int(raw_usage.get("input_tokens", 0)),
        output_tokens=int(raw_usage.get("output_tokens", 0)),
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
    return text, usage
