# ShopFix live benchmark results (real AWS + real git)

**Last updated:** 2026-05-17  
**Account:** `137792805243` (us-east-1)  
**Config:** `HELM_MOCK_BEDROCK=0`, `HELM_GATE_ENABLED=1`, `LIVE_AGENT_MAX_TOKENS=2048`, `LIVE_AGENT_REASSIGN_MAX_TOKENS=1024`  
**Fixture:** `shopfix/` at repo root (Etsy-style FastAPI + React, copied into temp git repos per run)  
**Raw JSON:** `results/shopfix_live_20260517_070051.json`, `shopfix_live_20260517_070205.json`, `shopfix_live_20260517_070543.json`

These numbers come from **`python scripts/run_shopfix_live_benchmark.py`** — Haiku agent edits on branches, git merge, pytest quality gate, Sonnet fleet dedup when the contention gate tier is `arbitrate`. No mock Bedrock.

---

## Executive summary

| Suite | N | Baseline (USD / time) | Helm (USD / time) | Sonnet dedup | Gate | Cost Δ | Notes |
|-------|---|------------------------|-------------------|--------------|------|--------|-------|
| **disjoint** | 2 | $0.0066 / 11.4s | $0.0063 / 11.1s | **0** | allow | ~4% | 0 Bedrock coordination calls |
| **disjoint** | 4 | $0.012 / 23.3s | $0.012 / 16.4s | **0** | allow | ~0% | **29% faster**; helm tests pass |
| **disjoint** | 6 | $0.019 / 21.9s | $0.019 / 22.0s | **0** | allow | ~0% | Same Haiku spend; no fleet dedup |
| **contention** | 2 | $0.012 / 15.8s | $0.015 / 18.9s | 1× Haiku dedup | arbitrate | −21% | Same-file auth cluster; 2 impl + merge-fix |
| **contention** | 4 | $0.021 / 23.7s | $0.033 / 31.4s | **1× Sonnet** | arbitrate | −56% | Fleet dedup + 2 cont + 2 reassign |
| **contention** | 6 | $0.028 / 28.6s | $0.045 / 40.7s | **1× Sonnet** | arbitrate | −64% | Auth + listings clusters |

**Primary win (disjoint / happy path):** contention gate tier `allow` → **zero** `helm-dedup` / Sonnet fleet calls while agents work on disjoint files in a real repo.

**Contention runs:** gate correctly detects file clusters and invokes dedup, but this harness still runs **continuation + reassignment** branches (same agent count as baseline for N≤6), so Sonnet coordination **adds** cost until we skip redundant full implementations on clustered files.

**Quality gate:** pytest on merged tree is **non-deterministic** — Haiku often adds auth helpers that do not exist (`get_current_user`, etc.). Treat `tests_pass` as diagnostic, not a stable headline metric yet.

---

## Disjoint suite (no file clusters)

Agents touch different modules (`auth`, `listings`, `cart`, …). Gate tier **`allow`** every time.

| N | Baseline USD | Helm USD | Baseline dedup | Helm dedup | Helm gate_skipped |
|---|--------------|----------|----------------|------------|-------------------|
| 2 | 0.006553 | 0.006263 | — | **0** | true |
| 4 | 0.011965 | 0.012355 | — | **0** | true |
| 6 | 0.018721 | 0.018551 | — | **0** | true |

**Example (N=4):** `gate_assessment.gate_tier=allow`, `file_clusters={}`, helm usage = **4× Haiku only** (agent_a…d), **0× Sonnet**.

---

## Contention suite (overlapping files)

| N | File clusters (gate) | Helm Sonnet calls | Helm continuations | Helm reassignments |
|---|---------------------|-------------------|--------------------|--------------------|
| 2 | `auth.py` ×2 | 0 (Haiku dedup) | agent_a | agent_b |
| 4 | `auth.py` ×3 | 1 fleet | agent_a, agent_d | agent_b, agent_c |
| 6 | `auth.py` ×3, `listings.py` ×2 | 1 fleet | agent_a, agent_d, agent_f | agent_b, agent_c, agent_e |

**Example (N=6) Sonnet fleet call:** `helm-dedup-fleet`, 2648 in / 466 out tokens, ~$0.01+ of helm path; total helm **$0.045** vs baseline **$0.028**.

---

## Reproduce

```bash
cd helm
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# ShopFix backend tests (once)
cd shopfix/backend && python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pytest -q && cd ../../helm

export HELM_MOCK_BEDROCK=0 HELM_GATE_ENABLED=1 AWS_DEFAULT_REGION=us-east-1
export LIVE_AGENT_MAX_TOKENS=2048 LIVE_AGENT_REASSIGN_MAX_TOKENS=1024

# Single case
python scripts/run_shopfix_live_benchmark.py --suite disjoint --agents 4

# Full matrix (costs real money)
python scripts/run_shopfix_live_benchmark.py --suite all --agents 2,4,6
```

Requires Bedrock access to **Claude Haiku 4.5** and **Sonnet 4.6** inference profiles in `us-east-1`.
