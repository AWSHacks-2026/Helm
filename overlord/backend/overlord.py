from __future__ import annotations

import json
import os
from typing import Any

from bedrock.client import get_bedrock_client
from models import BedrockArbitrationResult
from overlord_parse import extract_json_object
from overlord_prompt import build_merge_conflict_prompt

OVERLORD_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"
MAX_TOKENS = 1500


def arbitrate(agent_a: dict, agent_b: dict, kb_context: str | None = None) -> dict[str, Any]:
    """Call Sonnet via Bedrock to resolve a merge conflict between two agents."""
    client = get_bedrock_client()
    prompt = build_merge_conflict_prompt(agent_a, agent_b)
    if kb_context:
        prompt += f"\n\nRelevant history from Knowledge Base:\n{kb_context}"

    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        return _mock_merge_resolution()

    response = client.invoke_model(
        modelId=OVERLORD_MODEL,
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


def _mock_merge_resolution() -> dict[str, Any]:
    return {
        "conflict_type": "merge_conflict",
        "reasoning": "MOCK: Combined Agent A caching with Agent B type hints.",
        "resolved_code": (
            "def get_user(user_id: str) -> User:\n"
            "    if user_id in cache:\n"
            "        return cache[user_id]\n"
            "    result = db.query(user_id)\n"
            "    cache[user_id] = result\n"
            "    return result\n"
        ),
        "tokens_saved_estimate": "~2400 (mock)",
    }
