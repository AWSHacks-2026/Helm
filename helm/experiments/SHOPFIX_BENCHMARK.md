# ShopFix Git Benchmark

Compares **baseline** (blind git merges) vs **Helm** (intent API + contention gate) on the ShopFix Etsy-lite app at **[`../../shopfix/`](../../shopfix/)** (repo root).

## Prerequisites

- Python 3.11 for ShopFix backend and Helm backend
- Node 20+ for ShopFix frontend builds inside verify step
- Helm API running: `cd helm/backend && uvicorn main:app --port 8000`

## Run

From `helm/`:

```bash
export HELM_MOCK_BEDROCK=1 HELM_GATE_ENABLED=1
python scripts/run_shopfix_benchmark.py --suite all --agents 2,4 --mock
```

Results: `helm/experiments/results/shopfix_<timestamp>.json`

### Live (real AWS) benchmarks

```bash
export HELM_MOCK_BEDROCK=0 HELM_GATE_ENABLED=1 AWS_DEFAULT_REGION=us-east-1
python scripts/run_shopfix_live_benchmark.py --suite disjoint --agents 4
```

Results: [`SHOPFIX_LIVE_RESULTS.md`](SHOPFIX_LIVE_RESULTS.md) and `experiments/results/shopfix_live_*.json`.

Override fixture path: `SHOPFIX_FIXTURE_DIR=/path/to/shopfix` (default resolves to repo-root `shopfix/`).

## Judge demo (browse the app)

From repo root:

```bash
cd shopfix/backend && python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python scripts/seed.py
uvicorn app.main:app --port 8001

cd shopfix/frontend && npm ci && npm run dev
# http://localhost:5173 — login weaver@shopfix.test / demo1234
```

## Gates

| Suite | Helm must |
|-------|-----------|
| disjoint | Cost ≤10% baseline, time ≤115% baseline, tests pass |
| contention | Cost ≤70% baseline, time ≤70% baseline, tests pass |
