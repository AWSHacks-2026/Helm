# Overlord Backend

## Setup

```bash
cd overlord
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add AWS credentials
```

## Run tests

```bash
pytest -v
```

## Run API (mock Bedrock)

```bash
export OVERLORD_MOCK_BEDROCK=1
cd backend && uvicorn main:app --reload --port 8000
```

## Live Bedrock resolve

```bash
unset OVERLORD_MOCK_BEDROCK
cd backend && uvicorn main:app --port 8000
curl -s -X POST http://localhost:8000/resolve/merge_conflict | python -m json.tool
```

Requires Bedrock access to `us.anthropic.claude-sonnet-4-20250514-v1:0` in `us-east-1`.

## Demo scenarios (three acts)

| Act | Scenario | How to run |
|-----|----------|------------|
| 1 | `merge_conflict` | `POST /resolve/merge_conflict` |
| 2 | `intent_conflict` | `POST /resolve/intent_conflict` |
| 3 | `guardrail_prevention` | `POST /guardrail/check` |

### Quick verify (mock Bedrock)

```bash
export OVERLORD_MOCK_BEDROCK=1
cd backend && uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs or:

```bash
curl -s http://localhost:8000/demo/smoke | python3 -m json.tool
```

Expected: `"all_passed": true` and three checks with `"passed": true`.
