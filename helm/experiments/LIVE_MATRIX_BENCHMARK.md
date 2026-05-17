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

## Full matrix (after smoke)

```bash
python scripts/run_live_matrix_benchmark.py \
  --apps shopfix,streamcast \
  --agents 2,4,8 \
  --suites contention,disjoint
```

## Output

- `experiments/results/live_matrix_<timestamp>.json`
- `experiments/results/LIVE_MATRIX_RESULTS.md`

## Mock CI smoke

```bash
HELM_MOCK_BEDROCK=1 python scripts/run_live_matrix_benchmark.py \
  --apps shopfix --agents 2 --suites contention --allow-mock \
  --cells shopfix:contention:2
```
