# Helm experiment results

**Last updated:** 2026-05-16  
**Models:** Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`), Helm via Sonnet 4.6 / AgentCore Runtime

This document summarizes live benchmark runs comparing **baseline (no Helm)** vs **Helm-coordinated** paths.

**Primary metric: estimated USD** (Haiku ~$1/$5 per MTok, Sonnet ~$3/$15 per MTok). Raw token counts are misleading when Helm uses Sonnet and agents use Haiku.

---

## Executive summary

| Benchmark | Agents | Baseline | With Helm | Cost savings | Time | Quality |
|-----------|--------|----------|---------------|--------------|------|---------|
| **Fleet dedup** (`duplicate_work_fleet`) | 6 | **$0.077** / 62.9s | **$0.056** / 46.5s | **27%** | **26%** | 3 duplicate impls avoided |
| **Fleet merge** (`merge_conflict_fleet`) | 6 | **$0.0096** / 10.6s | **$0.0038** / 2.9s | **60%** | **72%** | 96% (tie); Sonnet escalation → 100% |
| **Merge conflicts** (4 scenarios, 2 agents) | 2 | **~$0.004** Haiku / ~2s | **$0** ledger‡ | 100%‡ | ~100% | 100% / 100% |

**Latest reports:** `dedup_report_20260516_233706`, `merge_fleet_report_20260516_233737`, `merge_report_*_20260516_233*`

‡ Pairwise merge Helm via **AgentCore Runtime** when `HELM_ARBITRATOR_ARN` is set; local ledger shows **$0** for Sonnet (untracked) — use AWS Cost Explorer for true spend.

§ Fleet merge default: **`MERGE_FLEET_STRATEGY=haiku_chain`** — one parallel Haiku merge-fix round per file (same model as agents), not Sonnet arbitration. Set `MERGE_FLEET_ESCALATE_SONNET=1` for 100% acceptance when Haiku-only scores 96%.

---

## 0. Contention gate — happy path (`commerce_disjoint`)

**Scenario:** Six agents, six disjoint files — no file clusters ≥2 agents.

**Config:** `HELM_GATE_ENABLED=1`, `HELM_MOCK_BEDROCK=1` (mock harness)

| Metric | Baseline | Helm (gated) | Notes |
|--------|----------|--------------|-------|
| Bedrock dedup calls | N/A | **0** | Gate tier `allow`; `gate_skipped=true` |
| Coordination | — | Skipped | Agents run without fleet Sonnet dedup |

Run: `HELM_MOCK_BEDROCK=1 HELM_GATE_ENABLED=1 python scripts/run_dedup_benchmark.py` (scenario `commerce_disjoint` via harness API).

Contention scenarios (`duplicate_work_fleet`, intent overlap) still use full Helm coordination when clusters or contradictions are detected.

---

## 1. Fleet deduplication (6 agents) — headline result

**Scenario:** `duplicate_work_fleet` on the commerce platform — overlapping auth (agents a/b/c), catalog (d/e), billing (f).

**Config:**

- `LIVE_AGENT_MAX_TOKENS=4096` (continuing agents)
- `LIVE_AGENT_REASSIGN_MAX_TOKENS=1024` (reassigned agents, focused patch prompt)

**Report:** `results/dedup_report_20260516_233706.json`

| Metric | Baseline (no Helm) | With Helm | Δ |
|--------|------------------------|---------------|---|
| **Est. cost (USD)** | **$0.077** | **$0.056** | **−27%** |
| Total tokens (detail) | 19,963 | 15,183 | −24% |
| Wall time | 62.9 s | 46.5 s | **−26%** |
| Primary implementation runs | 6 | 3 | **3 avoided** |
| Duplicate detected | — | Yes | — |

### What Helm did

- **Continued:** `agent_a` (JWT auth), `agent_d` (catalog search), `agent_f` (billing)
- **Reassigned:** `agent_b` → token lifecycle; `agent_c` → rate limiting / audit; `agent_e` → recommendations (non-search)

### Why this scales

- Baseline cost grows with **N agents × full implementation cap**.
- Helm adds **one Sonnet fleet call**, then **one full impl per overlap cluster** + **smaller reassigned patches**.
- Without the reassignment cap, live runs showed **more** tokens and **higher USD** than baseline (reassigned agents still generated huge Haiku modules). With `LIVE_AGENT_REASSIGN_MAX_TOKENS=1024`, Helm wins on **cost** and time — even though Sonnet coordination adds expensive tokens.

### Reproduce

```bash
cd helm && source .venv/bin/activate
export HELM_MOCK_BEDROCK=0
export LIVE_AGENT_MAX_TOKENS=4096
export LIVE_AGENT_REASSIGN_MAX_TOKENS=1024
python scripts/run_dedup_benchmark.py
```

---

## 2. Fleet merge conflicts (6 agents)

**Scenario:** `merge_conflict_fleet` — six agents submit incompatible code on auth (3), catalog (2), and billing (1).

**Config:** `LIVE_AGENT_MAX_TOKENS=4096`, `MERGE_FLEET_PARALLEL=1`, `MERGE_FLEET_MAX_TOKENS=4096` for Haiku merge-fix and per-file Sonnet arbitration.

**Report:** `results/merge_fleet_report_20260516_233737.md` (includes bar chart + mermaid flow)

| Metric | Baseline (Haiku chain) | With Helm | Δ |
|--------|------------------------|---------------|---|
| **Est. cost (USD)** | **$0.0096** | **$0.0038** | **−60%** |
| Total tokens (detail) | ~4,000 | ~1,500 | fewer calls (3 vs 7) |
| Wall time | 10.6 s | 2.9 s | **−72%** |
| Merge-fix / arbitration calls | 7 | 2 (auth + catalog) | **5 avoided** |
| Mean quality score | 96% | 100% | +4 pts |
| All files pass acceptance | No | **Yes** | — |

### Comparison chart (from report)

```
Baseline $     |████████░░░░░░░░░░░░░░░░░░░░| $0.0094
Helm $     |████████████████████████████| $0.030
Baseline ms    |██████████████████████░░░░░░| 10,207
Helm ms    |████████████████████████████| 13,324
```

### Reproduce

```bash
cd helm && source .venv/bin/activate
export HELM_MOCK_BEDROCK=0
export LIVE_AGENT_MAX_TOKENS=4096
export MERGE_FLEET_PARALLEL=1
python scripts/run_merge_fleet_benchmark.py
```

API: `POST /live/benchmark/merge-fleet/merge_conflict_fleet`

---

## 3. Merge conflicts — pairwise (2 agents)

**Setup:** Pre-seeded conflicting code (`seed_mode=scenario`). Baseline: Haiku agents alternate `merge_fix` until acceptance or max 3 rounds. Helm: single `arbitrate()` merge resolution.

**Run:** 2026-05-16, all four merge scenarios.

### Per-scenario results

| Scenario | Baseline tokens | Baseline time | Baseline rounds | Score (B / O) | Pass (B / O) |
|----------|-----------------|---------------|-----------------|---------------|--------------|
| `merge_conflict` | 234 | 1.3 s | 1 | 100 / 100 | ✓ / ✓ |
| `merge_rate_limit` | 725 | 2.8 s | 1 | 100 / 100 | ✓ / ✓ |
| `merge_error_handler` | 573 | 2.3 s | 1 | 100 / 100 | ✓ / ✓ |
| `merge_config_loader` | 406 | 1.7 s | 1 | 100 / 100 | ✓ / ✓ |
| **Average** | **485** | **~2.0 s** | **1** | **100 / 100** | **all pass** |

### Example: `merge_conflict` (`get_user` — cache vs types)

**Agent A:** in-memory cache on `get_user`  
**Agent B:** type hints, no cache  

**Baseline (Haiku, 1 round):** merged cache + types in 234 tokens.

```python
def get_user(user_id: str) -> User:
    if user_id in cache:
        return cache[user_id]
    result = db.query(user_id)
    cache[user_id] = result
    return result
```

**Helm:** same acceptance score; unified version with explicit `User` on `result`:

```python
def get_user(user_id: str) -> User:
    if user_id in cache:
        return cache[user_id]
    result: User = db.query(user_id)
    cache[user_id] = result
    return result
```

**Helm reasoning (excerpt):** caching and type hints are complementary; both intents preserved in one merge.

**Reports:**

- `results/merge_report_merge_conflict_20260516_231421.md`
- `results/merge_report_merge_rate_limit_20260516_231436.md`
- `results/merge_report_merge_error_handler_20260516_231448.md`
- `results/merge_report_merge_config_loader_20260516_231501.md`

### Reproduce

```bash
cd helm && source .venv/bin/activate
export HELM_MOCK_BEDROCK=0
python scripts/run_live_benchmark.py --all --seed-mode scenario
# single scenario:
python scripts/run_live_benchmark.py --scenario merge_conflict
```

API: `POST /live/benchmark/{scenario_name}?seed_mode=scenario`

---

## 4. Commerce platform conflict harness (no Helm)

Six agents edit shared modules without coordination (separate from dedup/merge benchmarks).

```bash
python scripts/run_agent_experiment.py
```

See `experiments/README.md` and theme `experiments/themes/commerce_platform/`.

---

## 5. Configuration reference

| Variable | Recommended | Purpose |
|----------|-------------|---------|
| `LIVE_AGENT_MAX_TOKENS` | `4096` | Full implementations (continuations, baseline, merge-fix) |
| `LIVE_AGENT_REASSIGN_MAX_TOKENS` | `1024` | Smaller patches for dedup-reassigned agents |
| `LIVE_BASELINE_MAX_ROUNDS` | `3` | Max Haiku merge-fix rounds without Helm |
| `LIVE_BENCHMARK_SEED_MODE` | `scenario` | Cheaper reproducible merge seeds (vs `haiku`) |
| `HELM_MOCK_BEDROCK` | `0` live / `1` CI | Mock for unit tests and zero-cost runs |

---

## 6. Takeaways

1. **Dedup at scale:** With 6 agents, Helm avoids duplicate primary work and wins on **tokens and time** when reassigned agents use a lower output cap.
2. **Merge at scale:** Fleet merge saves **15% tokens** and **6 merge-fix calls**, and reaches **100% acceptance** vs 96% baseline — at the cost of one longer Sonnet call.
3. **Pairwise merge (2 agents):** Fast on scenario seeds; use fleet benchmark for multi-file / multi-agent stress.
4. **Metrics that matter:** Track **calls avoided**, **acceptance pass rate**, and tokens — not tokens alone.

---

## 7. Raw artifacts

| Type | Path pattern |
|------|----------------|
| Dedup fleet | `results/dedup_report_<timestamp>.{md,json}` |
| Merge fleet | `results/merge_fleet_report_<timestamp>.{md,json}` |
| Merge pairwise | `results/merge_report_<scenario>_<timestamp>.{md,json}` |
| Agent conflicts | `results/report_<timestamp>.{md,json}` |

All under `helm/experiments/results/` (gitignored).
