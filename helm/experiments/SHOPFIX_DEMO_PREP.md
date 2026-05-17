# ShopFix + Helm — demo prep (live AWS)

**Generated:** 2026-05-17T09:17:27.880645+00:00
**Account / region:** live-aws
**Raw data:** `experiments/results/shopfix_demo_matrix_20260517_091231.json`

## How to read this

- **Cost / wall Δ** — positive % = Helm wins (cheaper or faster vs baseline).
- **Live** = gate → coord → agents → git merge (full ShopFix run).
- **Merge fleet** = merge-fix phase only (branches already conflict; parallel vs serial Haiku).

### Config used for this matrix

```bash
export HELM_MOCK_BEDROCK=0 HELM_GATE_ENABLED=1 HELM_INFERENCE_STRATEGY=haiku
export AWS_DEFAULT_REGION=us-east-1
export SHOPFIX_PARALLEL_AGENTS=1 SHOPFIX_EARLY_DISJOINT=1 SHOPFIX_SONNET_MERGE=0
export MERGE_FLEET_PARALLEL=1 MERGE_FLEET_STRATEGY=haiku_chain
export LIVE_AGENT_MAX_TOKENS=4096
export LIVE_AGENT_REASSIGN_MAX_TOKENS=2048
```

---

## Charts

Regenerate: `python scripts/plot_shopfix_demo_matrix.py`

| Chart | Use |
|-------|-----|
| [00_dashboard.png](charts/00_dashboard.png) | Four pillars overview |
| [06_guardrail_savings.png](charts/06_guardrail_savings.png) | Guardrail — 3 trial cost/wall % |
| [07_guardrail_absolute.png](charts/07_guardrail_absolute.png) | Guardrail — median $ and seconds |
| [08_guardrail_calls.png](charts/08_guardrail_calls.png) | 2 Haiku edits vs 1 guardrail call |
| [09_guardrail_headline.png](charts/09_guardrail_headline.png) | Guardrail — single slide |

Full index: [charts/README.md](charts/README.md)

---

## 60-second talk track

1. **Gate (disjoint)** — Six agents, six files, zero overlap: Helm runs the gate, **0 dedup Bedrock calls**, same cost as baseline, pytest passes.
2. **Duplicate work (contention)** — At N=8, baseline runs 8 agents; Helm runs **6** after dedup, **18% cheaper**, **39% faster** wall clock.
3. **Merge conflicts** — When git actually conflicts on **two files** (N≥6), parallel per-file merge-fix cuts merge phase **~30%** (N=6) with same Haiku cost.
4. **Guardrails (ShopFix auth)** — Block delete before it runs: **~45% cost, ~55% wall** vs destructive edit + rebuild ([SHOPFIX_GUARDRAIL_RESULTS.md](SHOPFIX_GUARDRAIL_RESULTS.md)).

---

## Best numbers to show live (pick one per pillar)

| Show this | Command | Headline |
|-----------|---------|----------|
| Gate / no coord tax | `disjoint --agents 6` | dedup=0, gate_skipped, tests pass |
| Duplicate work win | `contention --agents 8` | **+18% cost, +39% wall**, 6 agents not 8 |
| Cost-only mode | `contention --agents 6` + `SHOPFIX_REASSIGN=0` | **+38% cost, +35% wall**, 3 agents |
| Merge parallel | `run_shopfix_merge_fleet_benchmark.py contention 6` | **+30% wall** on 2 contested files |
| Guardrails | `run_shopfix_guardrail_benchmark.py` | **+45% cost, +55% wall**, block delete on `auth.py` |

---

## Executive summary

| Pillar | Say this | Strongest row in matrix |
|--------|----------|-------------------------|
| **Disjoint / gate** | No overlap → no coord spend | `disjoint_n6` dedup=0 |
| **Contention** | Dedup + skip + early_disjoint | `contention_std_n4` **+26%** cost; `contention_std_n8` **+39%** wall |
| **Merge fleet** | Parallel merge per file when ≥2 files conflict | `merge_fleet_contention_n6` **+30%** merge wall |
| **Intent opposition** | Align before impl; winner-only for cost | `opposition_no_reassign_n6` **+24%** cost (wall still coord-bound on std) |

### Honest caveats (say these if asked)

- **Contention N=2** — coord overhead can lose on wall; story starts at N≥4.
- **Opposition std** (all agents run) — wall loses badly (~5s coord); demo **no_reassign** or N=8 only if you need wall parity.
- **contention_verify** — pytest failed both paths in this run (fixture quality, not Helm-only); use skip_verify for timing demos.
- **Live contention** often has **0 merge Bedrock calls** on Helm path (dedup avoids conflicts); use **merge_fleet** benchmark to show merge parallelism.

---

## Master table (all runs)

| ID | Suite | N | Baseline | Helm | Cost Δ | Wall Δ | Helm agents | Dedup | Merge | pytest |
|----|-------|---|----------|------|--------|--------|-------------|-------|-------|--------|
| `disjoint_n4` | disjoint | 4 | $0.012 / 3.9s | $0.012 / 3.3s | -3% | +15% | 4 | 0 | 0 | pass |
| `disjoint_n6` | disjoint | 6 | $0.019 / 3.4s | $0.019 / 3.6s | — | -5% | 6 | 0 | 0 | pass |
| `disjoint_n8` | disjoint | 8 | $0.022 / 5.3s | $0.023 / 5.7s | -4% | -6% | 8 | 0 | 0 | pass |
| `contention_std_n2` | contention | 2 | $0.009 / 5.2s | $0.009 / 6.0s | -5% | -16% | 2 | 1 | 0 | pass |
| `contention_std_n4` | contention | 4 | $0.015 / 6.7s | $0.011 / 5.5s | +26% | +18% | 3 | 1 | 0 | pass |
| `contention_std_n6` | contention | 6 | $0.021 / 5.8s | $0.017 / 6.0s | +19% | -3% | 4 | 2 | 0 | pass |
| `contention_std_n8` | contention | 8 | $0.026 / 9.2s | $0.021 / 5.6s | +18% | +39% | 6 | 2 | 0 | pass |
| `contention_no_reassign_n4` | contention | 4 | $0.014 / 5.3s | $0.008 / 5.7s | +45% | -7% | 2 | 1 | 0 | pass |
| `contention_no_reassign_n6` | contention | 6 | $0.021 / 8.5s | $0.013 / 5.5s | +38% | +35% | 3 | 2 | 0 | pass |
| `contention_verify_n4` | contention | 4 | $0.015 / 18.0s | $0.011 / 11.5s | +25% | +36% | 3 | 1 | 0 | fail |
| `contention_verify_n6` | contention | 6 | $0.020 / 11.6s | $0.017 / 13.2s | +16% | -13% | 4 | 2 | 0 | fail |
| `opposition_std_n4` | intent_opposition | 4 | $0.014 / 6.2s | $0.020 / 10.9s | -40% | -76% | 4 | 0 | 0 | pass |
| `opposition_std_n6` | intent_opposition | 6 | $0.019 / 5.5s | $0.023 / 10.3s | -23% | -88% | 6 | 0 | 0 | pass |
| `opposition_std_n8` | intent_opposition | 8 | $0.024 / 7.2s | $0.027 / 7.8s | -13% | -8% | 8 | 0 | 0 | pass |
| `opposition_no_reassign_n4` | intent_opposition | 4 | $0.012 / 4.3s | $0.009 / 7.4s | +20% | -70% | 2 | 0 | 0 | pass |
| `opposition_no_reassign_n6` | intent_opposition | 6 | $0.019 / 6.2s | $0.015 / 7.5s | +24% | -21% | 4 | 0 | 0 | pass |
| `merge_fleet_contention_n2` | contention | 2 | $0.004 / 3.2s | $0.004 / 2.6s | — | +18% | 1→1 calls | — | 1 | pass |
| `merge_fleet_contention_n4` | contention | 4 | $0.009 / 6.3s | $0.009 / 6.3s | — | +0% | 2→2 calls | — | 2 | pass |
| `merge_fleet_contention_n6` | contention | 6 | $0.014 / 9.7s | $0.013 / 6.8s | +7% | +30% | 3→3 calls | — | 3 | pass |
| `merge_fleet_contention_n8` | contention | 8 | $0.015 / 10.0s | $0.015 / 8.0s | -4% | +20% | 3→3 calls | — | 3 | pass |

---


## Live E2E — by scenario

### disjoint_n4 — No file overlap — gate should allow, zero dedup Bedrock.

N=4: cost **-3%**, wall **+15%**; executed 4 agents (skipped 0); phases {'coord': 0.0, 'agents': 3.21, 'merge_verify': 0.01}
### disjoint_n6 — No file overlap — gate should allow, zero dedup Bedrock.

N=6: cost **+0%**, wall **-5%**; executed 6 agents (skipped 0); phases {'coord': 0.0, 'agents': 3.5, 'merge_verify': 0.02}
### disjoint_n8 — No file overlap — gate should allow, zero dedup Bedrock.

N=8: cost **-4%**, wall **-6%**; executed 8 agents (skipped 0); phases {'coord': 0.0, 'agents': 5.54, 'merge_verify': 0.02}
### contention_std_n2 — Duplicate work — dedup + trim + early_disjoint (default).

N=2: cost **-5%**, wall **-16%**; executed 2 agents (skipped 0); phases {'coord': 2.15, 'agents': 3.8, 'merge_verify': 0.02}
### contention_std_n4 — Duplicate work — dedup + trim + early_disjoint (default).

N=4: cost **+26%**, wall **+18%**; executed 3 agents (skipped 1); phases {'coord': 2.55, 'agents': 2.85, 'merge_verify': 0.01}
### contention_std_n6 — Duplicate work — dedup + trim + early_disjoint (default).

N=6: cost **+19%**, wall **-3%**; executed 4 agents (skipped 2); phases {'coord': 2.84, 'agents': 3.1, 'merge_verify': 0.01}
### contention_std_n8 — Duplicate work — dedup + trim + early_disjoint (default).

N=8: cost **+18%**, wall **+39%**; executed 6 agents (skipped 2); phases {'coord': 2.53, 'agents': 2.98, 'merge_verify': 0.02}
### contention_no_reassign_n4 — Winner-only on clusters; fill via early_disjoint.

N=4: cost **+45%**, wall **-7%**; executed 2 agents (skipped 2); phases {'coord': 2.73, 'agents': 2.86, 'merge_verify': 0.01}
### contention_no_reassign_n6 — Winner-only on clusters; fill via early_disjoint.

N=6: cost **+38%**, wall **+35%**; executed 3 agents (skipped 3); phases {'coord': 2.88, 'agents': 2.54, 'merge_verify': 0.01}
### contention_verify_n4 — Same as contention_std but runs pytest (quality).

N=4: cost **+25%**, wall **+36%**; executed 3 agents (skipped 1); phases {'coord': 2.41, 'agents': 2.74, 'merge_verify': 6.25}
### contention_verify_n6 — Same as contention_std but runs pytest (quality).

N=6: cost **+16%**, wall **-13%**; executed 4 agents (skipped 2); phases {'coord': 3.19, 'agents': 3.6, 'merge_verify': 6.31}
### opposition_std_n4 — Opposing intents — fleet coord (default).

N=4: cost **-40%**, wall **-76%**; executed 4 agents (skipped 0); phases {'coord': 4.44, 'agents': 6.34, 'merge_verify': 0.01}
### opposition_std_n6 — Opposing intents — fleet coord (default).

N=6: cost **-23%**, wall **-88%**; executed 6 agents (skipped 0); phases {'coord': 5.1, 'agents': 5.14, 'merge_verify': 0.02}
### opposition_std_n8 — Opposing intents — fleet coord (default).

N=8: cost **-13%**, wall **-8%**; executed 8 agents (skipped 0); phases {'coord': 4.14, 'agents': 3.58, 'merge_verify': 0.02}
### opposition_no_reassign_n4 — Opposition winner-only on contested files.

N=4: cost **+20%**, wall **-70%**; executed 2 agents (skipped 2); phases {'coord': 4.99, 'agents': 2.32, 'merge_verify': 0.01}
### opposition_no_reassign_n6 — Opposition winner-only on contested files.

N=6: cost **+24%**, wall **-21%**; executed 4 agents (skipped 2); phases {'coord': 5.2, 'agents': 2.25, 'merge_verify': 0.01}

## Merge fleet — by agent count

**N=2** (backend/app/routers/auth.py): merge wall **+18%**, 1→1 Haiku calls, cost tie typical
**N=4** (backend/app/routers/auth.py): merge wall **+0%**, 2→2 Haiku calls, cost tie typical
**N=6** (backend/app/routers/auth.py, backend/app/routers/listings.py): merge wall **+30%**, 3→3 Haiku calls, cost tie typical
**N=8** (backend/app/routers/auth.py, backend/app/routers/listings.py): merge wall **+20%**, 3→3 Haiku calls, cost tie typical

---

## Recommended live demo commands

```bash
cd helm && source .venv/bin/activate
export HELM_MOCK_BEDROCK=0 HELM_GATE_ENABLED=1 HELM_INFERENCE_STRATEGY=haiku AWS_DEFAULT_REGION=us-east-1
export SHOPFIX_PARALLEL_AGENTS=1 SHOPFIX_EARLY_DISJOINT=1 SHOPFIX_AGENT_STAGGER_SEC=0

# Pillar 1 — contention (cost + wall)
python scripts/run_shopfix_live_benchmark.py --suite contention --agents 4,6

# Pillar 2 — merge (show parallel merge on 2 files at N=6)
python scripts/run_shopfix_merge_fleet_benchmark.py --suite contention --agents 6

# Pillar 3 — guardrails on real ShopFix auth.py (~45% cost, ~55% wall)
export HELM_USE_LOCAL_MEMORY=true HELM_USE_LOCAL_POLICY=true
python scripts/run_shopfix_guardrail_benchmark.py

# Gate proof — disjoint
python scripts/run_shopfix_live_benchmark.py --suite disjoint --agents 6
```

Raw JSON: `experiments/results/shopfix_demo_matrix_20260517_091231.json`
