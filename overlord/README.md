# Overlord Backend (merge conflict slice)

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
