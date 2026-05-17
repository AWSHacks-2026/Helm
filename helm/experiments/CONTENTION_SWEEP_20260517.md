# Contention live sweep — 2026-05-17

**Harness:** `python scripts/run_shopfix_live_benchmark.py --suite contention`  
**Raw JSON:** `results/shopfix_live_20260517_090551.json`

Full pipeline: gate → per-file dedup → trim → agents (`SHOPFIX_EARLY_DISJOINT=1`) → git merge → merge-fix if needed.

---

## Config (win path)

```bash
export HELM_MOCK_BEDROCK=0 HELM_GATE_ENABLED=1 HELM_INFERENCE_STRATEGY=haiku
export AWS_DEFAULT_REGION=us-east-1
export SHOPFIX_PARALLEL_AGENTS=1 SHOPFIX_AGENT_STAGGER_SEC=0
export SHOPFIX_EARLY_DISJOINT=1 SHOPFIX_REASSIGN=1 SHOPFIX_SONNET_MERGE=0
export SHOPFIX_SKIP_VERIFY=1 SHOPFIX_MAX_PARALLEL=6
```

---

## End-to-end — cost + wall + bedrock

| N | Baseline $ / wall | Helm $ / wall | Agents run (helm) | Skipped | Cost Δ | Wall Δ | Bedrock Δ | Dedup calls |
|---|-------------------|---------------|-------------------|---------|--------|--------|-----------|-------------|
| **2** | $0.0092 / 11.9s | **$0.0081** / **5.8s** | 2 | 0 | **+11%** | **+51%** | **+44%** | 1 |
| **4** | $0.015 / 5.9s | **$0.011** / **5.5s** | 3 | 1 (`agent_c`) | **+27%** | **+6%** | **+12%** | 1 |
| **6** | $0.020 / 5.4s | **$0.017** / 6.1s | 4 | 2 (`agent_c`, `agent_e`) | **+16%** | −13% | **+7%** | 2 |
| **8** | $0.026 / 8.3s | **$0.020** / **5.6s** | 6 | 2 (`agent_c`, `agent_e`) | **+20%** | **+32%** | **+12%** | 2 |

All runs: `tests_pass=True` (verify skipped), `sonnet_calls=0`, no merge Bedrock on helm path in ledger.

Positive **Cost / Wall / Bedrock Δ** = Helm wins vs baseline.

---

## Phase wall clock (helm only)

| N | `coord` | `agents` | `merge_verify` |
|---|---------|----------|----------------|
| 2 | 2.4s | 3.2s | ~0s |
| 4 | 2.7s | 2.7s | ~0s |
| 6 | 2.8s | 3.2s | ~0s |
| 8 | 2.8s | 2.7s | ~0s |

`coord` includes gate (local) + dedup + trim; fill agents overlap dedup when `SHOPFIX_EARLY_DISJOINT=1`.

---

## Layout by N (contention.yaml)

| N | Auth cluster | Listings | Fill |
|---|--------------|----------|------|
| 2 | agent_a, agent_b | — | — |
| 4 | agent_a, agent_b, agent_c | — | agent_d |
| 6 | agent_a, agent_b, agent_c | agent_d, agent_e | agent_f |
| 8 | + spill per loader | + spill | + more fill |

---

## Reproduce

```bash
cd helm && source .venv/bin/activate
python scripts/run_shopfix_live_benchmark.py --suite contention --agents 2,4,6,8
```

See also: [`CONTENTION_DEEP_DIVE.md`](CONTENTION_DEEP_DIVE.md) (earlier canonical N=4/6 run `081446`).
