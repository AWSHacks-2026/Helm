# Live Matrix Benchmark (ShopFix + Streamcast)

Real Bedrock numbers: **N ∈ {2, 4, 8}**, suites **contention** then **disjoint**, baseline vs Helm.

## Locked decisions

- Bedrock Haiku agents (automated), real git/commits/merges
- 10 tasks per cell from shared `tasks.yaml`; suite YAML = assignment policy only
- Helm ON: `POST /intents`, guardrails on every write, dedup when gate arbitrate
- Smoke order: **contention, N=2** first

## Prerequisites

```bash
aws login   # or aws sso login
export AWS_DEFAULT_REGION=us-east-1
cd helm && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # HELM_MOCK_BEDROCK=0
python scripts/verify_aws_setup.py --bedrock
./scripts/run_shared_helm.sh   # port 8000 for Helm path
```

## Smoke (N=2, contention only)

```bash
cd helm
export HELM_MOCK_BEDROCK=0 HELM_GATE_ENABLED=1
python scripts/run_live_matrix_benchmark.py \
  --apps shopfix,streamcast \
  --agents 2 \
  --suites contention \
  --cells shopfix:contention:2
```

## Full matrix (both apps, N=2/4/8, contention then disjoint)

```bash
cd helm
source .venv/bin/activate
export HELM_MOCK_BEDROCK=0 HELM_GATE_ENABLED=1 AWS_DEFAULT_REGION=us-east-1
# Helm API in another terminal: ./scripts/run_shared_helm.sh

python scripts/run_live_matrix_benchmark.py \
  --apps shopfix,streamcast \
  --agents 2,4,8 \
  --suites contention,disjoint
```

Runs **12 cells** (2 apps × 2 suites × 3 agent counts). Results include **token totals** per baseline/helm path in JSON and `LIVE_MATRIX_RESULTS.md`.

**Two ShopFix benchmark paths (both kept after merge with `main`):**

| Script | Purpose |
|--------|---------|
| `run_live_matrix_benchmark.py` | Unified **ShopFix + Streamcast** matrix; full 10-task queue via `live_matrix` engine |
| `run_shopfix_demo_matrix.py` | Teammate demo matrix (contention/disjoint/opposition, merge-fleet, charts) via `shopfix_live_benchmark.py` |

Frontend Control Tower reads `GET /demo/benchmark-manifest` and charts under `experiments/charts/`.

**Under the hood** (`?view=recorder`): scrubbable N=2 agent + Helm graph. Refresh live trace after a matrix run:

```bash
cd helm && python scripts/export_flight_trace_from_log.py --both
# optional: --matrix-json experiments/results/live_matrix_<timestamp>.json
```

Writes both traces from the same log (auto-picks newest `live_matrix_*.json` if `--matrix-json` omitted):

- `frontend/public/traces/contention-n2-live.json` — Helm path (guardrails, measured savings in `meta`)
- `frontend/public/traces/contention-n2-live-baseline.json` — baseline path (includes `merge_fix:` on auth.py)

## Output

- `experiments/results/live_matrix_<timestamp>.json`
- `experiments/results/LIVE_MATRIX_RESULTS.md`

## Mock CI smoke

```bash
HELM_MOCK_BEDROCK=1 python scripts/run_live_matrix_benchmark.py \
  --apps shopfix --agents 2 --suites contention --allow-mock \
  --cells shopfix:contention:2
```
