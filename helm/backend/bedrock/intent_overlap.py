from __future__ import annotations

import re

from bedrock.agentcore_policy import _CONTRADICTION_PAIRS

_STOP = frozenset(
    "a an the and or for on in to of is are with this that module file app".split()
)


def _tokens(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z0-9]+", text.lower())
        if t not in _STOP and len(t) > 2
    }


def intent_overlap_score(intent_a: str, intent_b: str) -> float:
    a, b = _tokens(intent_a), _tokens(intent_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def intents_conflict(intent_a: str, intent_b: str) -> bool:
    la, lb = intent_a.lower(), intent_b.lower()
    for positive, negative in _CONTRADICTION_PAIRS:
        if any(tok in la for tok in positive) and any(tok in lb for tok in negative):
            return True
        if any(tok in lb for tok in positive) and any(tok in la for tok in negative):
            return True
    return False


def path_prefix_overlap(path_a: str, path_b: str) -> bool:
    parts_a = [p for p in path_a.split("/") if p]
    parts_b = [p for p in path_b.split("/") if p]
    if len(parts_a) < 2 or len(parts_b) < 2:
        return path_a == path_b
    return parts_a[:2] == parts_b[:2]
