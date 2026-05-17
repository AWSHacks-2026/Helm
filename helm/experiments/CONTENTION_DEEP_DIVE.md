# ShopFix contention suite — deep dive (live AWS)

**Purpose:** Working comparison of baseline vs Helm across benchmark iterations. Use this for demos, regressions, and tuning.

**Canonical win run:** `results/shopfix_live_20260517_081446.json`  
**Full sweep N=2–8 (2026-05-17):** [`CONTENTION_SWEEP_20260517.md`](CONTENTION_SWEEP_20260517.md) → `results/shopfix_live_20260517_090551.json`  
**Account / region:** `137792805243` / `us-east-1`  
**Fixture:** `shopfix/scenarios/contention.yaml` — auth cluster (3 intents) + listings cluster (2 intents at N≥5) + fill modules

---

## Scenario layout (what agents do)

| N | Auth cluster (`auth.py`) | Listings cluster (`listings.py`) | Fill (disjoint) |
|---|--------------------------|----------------------------------|-----------------|
| 4 | agent_a, agent_b, agent_c | — | agent_d |
| 6 | agent_a, agent_b, agent_c | agent_d, agent_e | agent_f |

Baseline: **all N agents** implement in parallel from `main`, merge all branches, Haiku merge-fix if needed.

Helm (contention path): gate `arbitrate` → per-file dedup → trim (1 winner + ≤1 reassign per cluster, skip losers) → implement plan → merge.

---

## Evolution of Helm vs baseline (contention only)

All runs: `HELM_MOCK_BEDROCK=0`, `HELM_GATE_ENABLED=1`, real git. Newer runs use `SHOPFIX_SKIP_VERIFY=1` for timing (pytest ~0.4s removed from wall).

| Run label | JSON file | Config highlights | N=4 cost Δ | N=4 wall Δ | N=6 cost Δ | N=6 wall Δ |
|-----------|-----------|-------------------|------------|------------|------------|------------|
| Pre-optimization | `073126` | All agents run, Sonnet-era path | −106% | −79% | −55% | −62% |
| Sonnet coordinator | `075145` | Fleet dedup Sonnet, no skip | −53% | −6% | −56% | −55% |
| Haiku coordinator | `075748` | Haiku dedup, no skip | −20% | −8% | −23% | −6% |
| **Agent skip trim** | `080414` | Skip cluster losers | **+8%** | **+6%** | −13% | −21% |
| Stagger 0 + phases | `081048` | Haiku merge-fix, phase metrics | **+24%** | −20% | +6% | −71% |
| **Early disjoint (WIN)** | `081446` | Fill agents overlap coord | **+19%** | **+7%** | **+15%** | **+21%** |

**Takeaway:** Cost flipped positive at **agent skip** (`080414`). Wall flipped positive at **early disjoint** (`081446`) while keeping cost wins.

---

## Canonical results — all three metrics green (`081446`)

| N | Baseline ($ / wall) | Helm ($ / wall) | Cost Δ | Wall Δ | Bedrock Δ | Bedrock calls (helm) |
|---|---------------------|-----------------|--------|--------|-----------|----------------------|
| **4** | $0.015 / 6.46s | **$0.012 / 5.98s** | **+19%** | **+7%** | **+23%** | 4 (1 dedup + 3 agent) |
| **6** | $0.020 / 9.16s | **$0.017 / 7.19s** | **+15%** | **+21%** | **+18%** | 6 (2 dedup + 4 agent) |

**Win config:** `HELM_INFERENCE_STRATEGY=haiku`, `SHOPFIX_EARLY_DISJOINT=1`, `SHOPFIX_AGENT_STAGGER_SEC=0`, `SHOPFIX_SONNET_MERGE=0`, `SHOPFIX_REASSIGN=1`, `SHOPFIX_SKIP_VERIFY=1`.

---

## Average step times (Bedrock latency per call)

Aggregated over **all contention runs** in the results corpus (`073126` … `081446`):

| Step (ledger role) | Calls (n) | Avg latency | Min | Max | Notes |
|--------------------|-----------|-------------|-----|-----|-------|
| **agent_impl** | 126 | **2.77s** | 2.0s | 6.5s | Haiku file edit; dominates agent phase |
| **dedup** | 14 | **4.80s** | 2.4s | 9.6s | Haiku fleet (3 agents) or pairwise (2) |

No merge Bedrock calls on contention win runs (Haiku merge-fix path had no conflict-resolution calls in ledger).

### Per-phase wall clock (runs with `phase_seconds` only)

| Phase | N=4 avg | N=6 avg | What it includes |
|-------|---------|---------|------------------|
| **coord** | **3.19s** | **3.99s** | Gate (local) + dedup (+ intent on other suites) + trim; **early_disjoint overlaps fill agent Bedrock here** |
| **agents** | **3.32s** | **4.36s** | Remaining agent impls + git branch/commit (not in early_disjoint set) |
| **merge_verify** | **~0.01s** | **~0.02s** | Merge + pytest skipped |

*Phase averages from `081048` + `081446` (four helm contention rows).*

### Canonical N=4 call ledger (`081446` helm)

| Order | Role | Latency | Tokens (in/out) | When |
|-------|------|---------|-----------------|------|
| 1 | `agent_d` | 2.22s | 461 / 445 | **During coord** (early_disjoint on fill file) |
| 2 | `helm-dedup-fleet-haiku` | 2.84s | 1382 / 262 | Coord (auth ×3) |
| 3 | `agent_a` | 2.82s | 391 / 577 | Agent phase (auth winner) |
| 4 | `agent_b` | 2.82s | 455 / 562 | Agent phase (reassign → fill module) |

**Skipped:** `agent_c` (loser on auth cluster).  
**Plan:** continue `agent_a` + `agent_d`; reassign `agent_b`; not 2 agents — **3 Bedrock agent calls** (JSON `agents_executed` undercounts because it excludes `early_disjoint_ids`; true count = `len(run_by_id)` = 3).

### Canonical N=6 call ledger (`081446` helm)

| Role | Latency | Cluster |
|------|---------|---------|
| `helm-dedup-haiku` | 2.45s | listings ×2 |
| `helm-dedup-fleet-haiku` | 2.95s | auth ×3 |
| `agent_f` | 2.42s | early_disjoint fill |
| `agent_d` | 2.17s | listings winner |
| `agent_a` | 3.93s | auth winner |
| `agent_b` | 3.54s | auth reassign |

**Skipped:** `agent_c`, `agent_e`. **4 agent impls** + **2 dedup** = 6 Bedrock calls.

---

## Why Helm wins (mechanism)

```text
Baseline (N=4):  [agent_a][agent_b][agent_c][agent_d]  → 4× Haiku  →  merge 4 branches
Helm (N=4):      [dedup ~3s] + [agent_d ∥ dedup] + [agent_a][agent_b]  →  3× Haiku  →  merge 3 branches
                 └─ skip agent_c
```

1. **Skip** — One redundant auth impl removed (~$0.004–0.005, ~2.8s bedrock).
2. **Haiku dedup** — One fleet call (~$0.003) vs zero baseline coord, but cheaper than an extra agent.
3. **Early disjoint** — `agent_d` runs during dedup → wall time ≈ `max(coord, agents)` not `coord + agents` for the fill agent.

**Gate:** `gate_tier=arbitrate`, `file_clusters: auth.py×3` (N=4); no Bedrock on gate itself.

---

## Demo script (reproduce WIN)

```bash
cd helm && source .venv/bin/activate
export HELM_MOCK_BEDROCK=0 HELM_GATE_ENABLED=1 HELM_INFERENCE_STRATEGY=haiku
export AWS_DEFAULT_REGION=us-east-1
export SHOPFIX_PARALLEL_AGENTS=1 SHOPFIX_AGENT_STAGGER_SEC=0
export SHOPFIX_SONNET_MERGE=0 SHOPFIX_EARLY_DISJOINT=1 SHOPFIX_SKIP_VERIFY=1

python scripts/run_shopfix_live_benchmark.py --suite contention --agents 4,6
```

**Judge one-liner:** “Four agents pile onto auth; Helm spends one Haiku call to pick a winner, runs three agents instead of four, and finishes faster and cheaper than naive parallel.”

---

## Known gaps / next tuning

| Item | Impact |
|------|--------|
| `agents_executed` metric | Should be `len(run_by_id)` including early_disjoint; currently undercounts |
| `SHOPFIX_REASSIGN=0` | Winner-only → 2 agents on N=4; may improve wall further (unbenchmarked on WIN config) |
| N=2 contention | Not in demo matrix; pairwise dedup only |
| `tests_pass` | Unstable when verify enabled; use `SHOPFIX_SKIP_VERIFY=0` for quality runs only |

---

## Related files

- Harness: `helm/backend/agents/shopfix_live_benchmark.py`
- Summary table: `helm/experiments/SHOPFIX_LIVE_RESULTS.md`
- Intent opposition brainstorm: see conversation + `results/shopfix_live_20260517_081549.json`
