from __future__ import annotations

from dataclasses import dataclass, field

from services.token_estimates import parse_tokens_estimate


@dataclass
class GratitudeLedger:
    intents_declared: int = 0
    guardrails_blocked: int = 0
    intents_aligned: int = 0
    duplicates_avoided: int = 0
    agents_yielded: int = 0
    tokens_saved_total: int = 0
    tokens_saved_display: str = "0"
    haiku_calls: int = 0
    sonnet_calls: int = 0
    timeline: list[dict] = field(default_factory=list)


def build_gratitude_ledger(events: list[dict]) -> GratitudeLedger:
    ledger = GratitudeLedger()
    tokens = 0
    for ev in events:
        et = ev.get("event_type", "")
        payload = ev.get("payload", {})
        if et == "intent_declared":
            ledger.intents_declared += 1
        elif et in {"guardrail_blocked", "gratitude_handoff"}:
            ledger.guardrails_blocked += 1
            ledger.timeline.append(
                {
                    "kind": "yield",
                    "message": f"Blocked {payload.get('agent_id')} on {payload.get('file_path')}",
                    "at": ev.get("timestamp"),
                }
            )
        elif et == "intent_aligned":
            ledger.intents_aligned += 1
            tokens += parse_tokens_estimate(str(payload.get("tokens_saved_estimate", "")))
            tier = payload.get("inference_tier")
            if tier == "haiku":
                ledger.haiku_calls += 1
            elif tier == "sonnet":
                ledger.sonnet_calls += 1
        elif et == "mission_delegated" and payload.get("duplicate_detected"):
            ledger.duplicates_avoided += 1
            for assignment in payload.get("assignments", []):
                if assignment.get("action") == "reassign":
                    ledger.agents_yielded += 1
        elif et == "conflict_resolved":
            res = payload.get("resolution", payload)
            tokens += parse_tokens_estimate(str(res.get("tokens_saved_estimate", "")))
            tier = res.get("inference_tier") or res.get("resolution_tier")
            if tier == "haiku":
                ledger.haiku_calls += 1
            elif tier == "sonnet":
                ledger.sonnet_calls += 1
    ledger.tokens_saved_total = tokens
    ledger.tokens_saved_display = f"~{tokens:,} tokens" if tokens else "0"
    ledger.timeline = ledger.timeline[:10]
    return ledger
