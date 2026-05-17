from __future__ import annotations

import json
import os
from typing import Any

from bedrock.client import get_bedrock_client
from bedrock.model_ids import DEFAULT_HELM_BEDROCK_MODEL_ID, resolve_inference_profile_id
from models import BedrockArbitrationResult
from helm_parse import extract_json_object

from arbitration.prompt import build_merge_conflict_prompt

HELM_MODEL = resolve_inference_profile_id(
    os.getenv("HELM_BEDROCK_MODEL_ID")
    or os.getenv("HELM_BEDROCK_MODEL")
    or DEFAULT_HELM_BEDROCK_MODEL_ID
)
MAX_TOKENS = 1500


def run_arbitration(
    agent_a: dict,
    agent_b: dict,
    kb_context: str | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call Sonnet via bedrock-runtime invoke_model; return validated arbitration dict."""
    client = get_bedrock_client()
    prompt = build_merge_conflict_prompt(agent_a, agent_b)
    if kb_context:
        kb_text = (
            json.dumps(kb_context, indent=2)
            if isinstance(kb_context, list)
            else kb_context
        )
        prompt += f"\n\nRelevant history from Knowledge Base:\n{kb_text}"

    response = client.invoke_model(
        modelId=HELM_MODEL,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )

    payload = json.loads(response["body"].read())
    text = payload["content"][0]["text"]
    raw = extract_json_object(text)
    validated = BedrockArbitrationResult.model_validate(raw)
    return validated.model_dump()
