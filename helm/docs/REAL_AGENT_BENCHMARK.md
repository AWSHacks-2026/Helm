# Real-Agent Streamcast Benchmark

Prove Helm adds **minimal overhead** when agents edit disjoint files (independent suite) and **saves coordination cost** when they collide on the same file (conflicting suite).

## Prerequisites

1. Helm API running: `cd helm && ./scripts/run_shared_helm.sh`
2. Python deps: `pip install -r requirements.txt` (includes PyYAML)
3. Three Cursor windows (one per agent assignment)
4. Optional: `HELM_MOCK_BEDROCK=1` in `.env` for demos without live Bedrock

## Independent suite (disjoint modules)

```bash
cd helm
export HELM_ENABLED=0
./scripts/run_streamcast_benchmark.sh independent
# Complete each agent brief under benchmarks/suites/independent/agents/
python scripts/collect_streamcast_run.py --run-id <RUN_ID>

export HELM_ENABLED=1
./scripts/run_streamcast_benchmark.sh independent
python scripts/collect_streamcast_run.py --run-id <RUN_ID>

python scripts/collect_streamcast_run.py --run-id <OFF_RUN> --compare <OFF_RUN> <ON_RUN>
```

**Pass:** Helm ON uses ≤2 API calls per session and <10% wall-clock vs baseline.

## Conflicting suite (same file)

```bash
export HELM_ENABLED=0
./scripts/run_streamcast_benchmark.sh conflicting

export HELM_ENABLED=1
./scripts/run_streamcast_benchmark.sh conflicting
# On merge conflicts, use helm_resolve_conflict or POST /integrations/git/merge-conflict
```

**Pass:** Fewer conflict files, faster wall-clock, or ≥30% fewer coordination events vs baseline.

## Agent workflow

1. Open Cursor at the printed worktree path.
2. Paste the matching `agents/<agent_id>.md` brief.
3. With Helm ON: `helm_declare_intent` before first edit; pre-write hook enforces guardrails.
4. Commit: `feat(<agent_id>): <summary>`
5. Press Enter in the orchestrator terminal (or touch `.done` with `WAIT_MODE=file`).

## MCP & hooks

Configured under `benchmarks/streamcast/.cursor/`:

- `mcp.json` → `helm` server (`mcp/server.py`)
- `hooks.json` → `integrations/claude-code/pre-write.sh`

Set `HELM_ENABLED=0` to bypass guardrails for baseline runs.

## Results

- `benchmarks/results/<run_id>/meta.json` — run metadata
- `benchmarks/results/<run_id>/report.json` — collected metrics
- `benchmarks/results/compare-*/REPORT.md` — comparison table

Record manual dry-run notes in `benchmarks/results/README.md`.
