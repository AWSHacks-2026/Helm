"""Approximate Bedrock on-demand USD from token usage (for demos / benchmarks)."""

from __future__ import annotations

from typing import Any

# USD per token (us-east-1 inference profiles, approximate on-demand)
_RATES_PER_TOKEN: dict[str, tuple[float, float]] = {
    "haiku": (1.0e-6, 5.0e-6),   # ~$1 / $5 per MTok
    "sonnet": (3.0e-6, 15.0e-6),  # ~$3 / $15 per MTok
    "opus": (15.0e-6, 75.0e-6),
}


def model_tier(model_id: str) -> str:
    mid = (model_id or "").lower()
    if "haiku" in mid:
        return "haiku"
    if "opus" in mid:
        return "opus"
    if "sonnet" in mid or "claude" in mid:
        return "sonnet"
    return "sonnet"


def estimate_usd(model_id: str, input_tokens: int, output_tokens: int) -> float:
    tier = model_tier(model_id)
    in_rate, out_rate = _RATES_PER_TOKEN[tier]
    return input_tokens * in_rate + output_tokens * out_rate


def format_usd(amount: float) -> str:
    if amount < 0.01:
        return f"${amount:.4f}"
    if amount < 1.0:
        return f"${amount:.3f}"
    return f"${amount:.2f}"


def cost_from_usage(usage: dict[str, Any]) -> float:
    total = 0.0
    for call in usage.get("calls", []):
        total += estimate_usd(
            str(call.get("model_id", "")),
            int(call.get("input_tokens", 0)),
            int(call.get("output_tokens", 0)),
        )
    return total


def build_cost_comparison(
    baseline_usage: dict[str, Any],
    helm_usage: dict[str, Any],
) -> dict[str, Any]:
    """Cost-focused comparison; Sonnet-heavy Helm paths vs Haiku baseline."""
    b_cost = cost_from_usage(baseline_usage)
    o_cost = cost_from_usage(helm_usage)
    delta = b_cost - o_cost
    savings_pct = int(100 * delta / b_cost) if b_cost > 0 else 0
    return {
        "baseline_cost_usd": round(b_cost, 6),
        "helm_cost_usd": round(o_cost, 6),
        "cost_delta_usd": round(delta, 6),
        "cost_savings_pct": savings_pct,
        "helm_beats_cost": o_cost < b_cost,
        "baseline_cost_display": format_usd(b_cost),
        "helm_cost_display": format_usd(o_cost),
        "cost_note": (
            "Helm ledger shows $0 — merge may have used AgentCore Runtime (untracked)."
            if o_cost == 0 and helm_usage.get("call_count", 0) == 0
            else None
        ),
    }
