# ShopFix Git Benchmark

Compares **baseline** (blind git merges) vs **Helm** (intent API + contention gate) on the ShopFix Etsy-lite fixture.

## Prerequisites

- Python 3.11 for ShopFix backend and Helm backend
- Node 20+ for ShopFix frontend builds inside verify step
- Helm API running: `cd helm/backend && uvicorn main:app --port 8000`

## Run

```bash
export HELM_MOCK_BEDROCK=1 HELM_GATE_ENABLED=1
python helm/scripts/run_shopfix_benchmark.py --suite all --agents 2,4 --mock
```

Results: `helm/experiments/results/shopfix_<timestamp>.json`

## Judge demo (browse the app)

```bash
cd helm/fixtures/shopfix/backend && python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python scripts/seed.py
uvicorn app.main:app --port 8001

cd helm/fixtures/shopfix/frontend && npm ci && npm run dev
# http://localhost:5173 — login weaver@shopfix.test / demo1234
```

## Gates

| Suite | Helm must |
|-------|-----------|
| disjoint | Cost ≤10% baseline, time ≤115% baseline, tests pass |
| contention | Cost ≤70% baseline, time ≤70% baseline, tests pass |
