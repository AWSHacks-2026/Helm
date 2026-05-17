# Multi-agent experiments

## Commerce platform (single project)

Six Haiku agents edit `commerce_platform` modules. Several agents overlap on auth and catalog without Overlord.

| Agent | File | Overlap group |
|-------|------|----------------|
| agent_a, b, c | `app/auth/handlers.py` | Authentication |
| agent_d, e | `app/catalog/products.py` | Catalog search/listing |
| agent_f | `app/billing/invoices.py` | Unique (billing) |

## Metrics (conflict harness)

| Metric | Meaning |
|--------|---------|
| **Conflict edits** | Files where two agents produced different code |
| **Reverted commits** | Sequential apply lost prior agent content |
| **Est. cost (USD)** | Bedrock $ from per-call model rates (Haiku vs Sonnet) |
| **Total tokens** | Haiku/Sonnet input + output (secondary; see cost) |
| **Resolution time** | Wall-clock ms for agent calls |
| **Successful build rate** | Merged files still parse |

## Run conflict harness

```bash
cd overlord
source .venv/bin/activate
export OVERLORD_MOCK_BEDROCK=1
python scripts/run_agent_experiment.py --mock
```

Live:

```bash
export OVERLORD_MOCK_BEDROCK=0
export LIVE_AGENT_MAX_TOKENS=4096
export LIVE_AGENT_REASSIGN_MAX_TOKENS=1024
python scripts/run_agent_experiment.py
```

## Fleet dedup benchmark

```bash
python scripts/run_dedup_benchmark.py              # duplicate_work_fleet (6 agents)
python scripts/run_dedup_benchmark.py --mock
python scripts/run_dedup_benchmark.py --scenario duplicate_work  # 2-agent legacy
```

Output: `experiments/results/dedup_report_<timestamp>.md` and `.json`

## Results write-up

See **[EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md)** for live comparison tables (fleet dedup + merge conflicts).

## Merge benchmark (with vs without Overlord)

```bash
python scripts/run_live_benchmark.py --all --seed-mode scenario
```

Output: `experiments/results/merge_report_<scenario>_<timestamp>.md`

## Merge fleet benchmark (6 agents, 4096 tokens)

```bash
python scripts/run_merge_fleet_benchmark.py
python scripts/run_merge_fleet_benchmark.py --mock
```

Output: `experiments/results/merge_fleet_report_<timestamp>.md` (bar chart + mermaid)
