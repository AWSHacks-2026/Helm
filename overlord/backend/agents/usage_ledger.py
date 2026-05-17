from __future__ import annotations

from dataclasses import dataclass, field

from bedrock.cost_estimate import estimate_usd, format_usd
from bedrock.invoke_tracked import InvokeUsage


@dataclass
class UsageLedger:
    calls: list[InvokeUsage] = field(default_factory=list)

    def add(self, usage: InvokeUsage) -> None:
        self.calls.append(usage)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def total_latency_ms(self) -> int:
        return sum(c.latency_ms for c in self.calls)

    @property
    def estimated_cost_usd(self) -> float:
        return sum(
            estimate_usd(c.model_id, c.input_tokens, c.output_tokens) for c in self.calls
        )

    def to_dict(self) -> dict:
        cost = self.estimated_cost_usd
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(cost, 6),
            "estimated_cost_display": format_usd(cost),
            "total_latency_ms": self.total_latency_ms,
            "call_count": len(self.calls),
            "calls": [
                {
                    "model_id": c.model_id,
                    "role": c.role,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "latency_ms": c.latency_ms,
                }
                for c in self.calls
            ],
        }
