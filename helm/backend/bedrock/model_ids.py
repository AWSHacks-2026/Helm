"""Resolve Bedrock model IDs to on-demand inference profile IDs where required."""

from __future__ import annotations

# Default for Helm coordination (dedup, resolve, guardrail Sonnet-tier paths)
DEFAULT_HELM_BEDROCK_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def resolve_inference_profile_id(model_id: str) -> str:
    """
    Anthropic foundation model IDs (anthropic.*) cannot be invoked on-demand directly
    in many regions; Bedrock expects the matching inference profile (us.anthropic.*).
    ARNs and us.* IDs are passed through unchanged.
    """
    mid = (model_id or "").strip()
    if not mid:
        return mid
    if mid.startswith("arn:") or mid.startswith("us."):
        return mid
    if mid.startswith("anthropic."):
        return f"us.{mid}"
    return mid
