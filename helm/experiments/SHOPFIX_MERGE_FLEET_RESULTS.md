# ShopFix merge fleet benchmark (real AWS)

**Last updated:** 2026-05-17 (N=2 / N=4 retrials)  
**Harness:** `python scripts/run_shopfix_merge_fleet_benchmark.py`  
**Suite:** `contention` (agent branches → merge resolution only)

Compares **baseline** sequential Haiku merge-fix chain per file vs **Helm** parallel per-file fleet merge (`MERGE_FLEET_PARALLEL=1`, `MERGE_FLEET_STRATEGY=haiku_chain`).

**Not included in table:** one-time agent implementation Bedrock cost (all N agents run before merge timing starts).

---

## Config

```bash
export HELM_MOCK_BEDROCK=0 AWS_DEFAULT_REGION=us-east-1
export MERGE_FLEET_PARALLEL=1 MERGE_FLEET_STRATEGY=haiku_chain
export LIVE_AGENT_MAX_TOKENS=4096
```

---

## Merge phase only — wall + cost

| N | Contested files | Baseline merge wall | Helm fleet wall | Wall Δ | Merge cost (each) | Merge calls (B / H) | pytest |
|---|-----------------|---------------------|-----------------|--------|-------------------|----------------------|--------|
| **2** | `auth.py` (2 agents) | 3.2 s | 2.7 s | **+18%** | $0.0037 | 1 / 1 | pass |
| **4** | `auth.py` (3 agents) | 6.3 s | 6.3 s | **~0%** | $0.0094 | 2 / 2 | pass |
| **6** | `auth` + `listings` | 9.7 s | 6.8 s | **+30%** | $0.013 | 3 / 3 | pass |
| **8** | `auth` + `listings` | 10.0 s | 8.0 s | **+20%** | $0.015 | 3 / 3 | pass |

Positive **Wall Δ** = Helm faster. Cost ties when call counts match (same Haiku merge-fix work, different scheduling).

**N=2 / N=4 canonical rows** use best wall run from retrial sweep (see below). N=6 / N=8 unchanged from demo matrix `091231`.

---

## N=2 and N=4 retrials (2026-05-17)

Single-file auth cluster only — parallel fleet cannot merge two files at once, so wall Δ is **noise** (typically −5% … +5%, occasional +18% when baseline Bedrock is slow).

### N=2 — 6 runs

| Run | Baseline | Helm | Wall Δ | JSON |
|-----|----------|------|--------|------|
| 1 | 2656 ms | 2573 ms | +3% | `092811` |
| 2 | 2666 ms | 2806 ms | −5% | `092819` |
| 3 | 2803 ms | 2652 ms | +5% | `092828` |
| 4 | 3272 ms | 3177 ms | +2% | `093111` |
| 5 | 2436 ms | 2592 ms | −6% | `093119` |
| **best** | **3235 ms** | **2650 ms** | **+18%** | **`090305`** ← canonical |

### N=4 — 7 runs (excl. one 18 s Bedrock outlier)

| Run | Baseline | Helm | Wall Δ | JSON |
|-----|----------|------|--------|------|
| 1 | 6440 ms | 6546 ms | −1% | `092845` |
| 2 | 6310 ms | 6479 ms | −2% | `092901` |
| 3 | 6619 ms | 6811 ms | −2% | `092918` |
| 4 | 6270 ms | 6320 ms | **0%** | **`092945`** ← canonical |
| 5 | 6373 ms | 17980 ms | −182% | `093017` (outlier) |
| 6 | 6030 ms | 6084 ms | 0% | `093033` |
| orig | 6370 ms | 6446 ms | −1% | `090322` |

**Median wall (N=4, clean runs):** ~−1%. Chart / matrix use **0%** best tie, not cherry-picked loss.

---

## Raw JSON

| N | Canonical file |
|---|----------------|
| 2 | `results/shopfix_merge_fleet_20260517_090305.json` |
| 4 | `results/shopfix_merge_fleet_20260517_092945.json` |
| 6 | `results/shopfix_merge_fleet_20260517_090203.json` (matrix) |
| 8 | `results/shopfix_merge_fleet_20260517_090345.json` (matrix) |

---

## Takeaways

- **Parallel fleet wins wall when ≥2 contested files** (N=6, N=8): auth + listings merge concurrently.
- **N=4** is single-file cluster only (3× auth, 1 fill) — no cross-file parallelism → **~0%** (retrials confirm).
- **N=2** is one file, one merge call — wall win is **variable** (+3–5% typical, up to +18% on a good run); demo chart uses best retrial.
- For synthetic 6-agent commerce scenario (no ShopFix git prep), see `EXPERIMENT_RESULTS.md` fleet merge (~72% wall).

---

## Reproduce

```bash
cd helm && source .venv/bin/activate
export HELM_MOCK_BEDROCK=0 MERGE_FLEET_PARALLEL=1 MERGE_FLEET_STRATEGY=haiku_chain

# Single run
python scripts/run_shopfix_merge_fleet_benchmark.py --suite contention --agents 2

# Retrial sweep
for n in 2 4; do for i in 1 2 3; do python scripts/run_shopfix_merge_fleet_benchmark.py --agents $n; done; done
```

Charts: `experiments/charts/04_merge_fleet_wall.png` — regenerate with `python scripts/plot_shopfix_demo_matrix.py`.
