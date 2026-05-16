# Overlord

Supervisor service for multi-agent coding workflows. Resolves merge conflicts via Bedrock Sonnet, exposes APIs for IDE hooks (MCP / Claude Code), and includes a React dashboard.

## Setup

```bash
cd overlord
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # region + OVERLORD_MOCK_BEDROCK only; use aws login for creds
```

## Run backend

```bash
export OVERLORD_MOCK_BEDROCK=1   # or 0 for live Bedrock after aws login
cd backend && uvicorn main:app --reload --port 8000
```

- API docs: http://127.0.0.1:8000/docs
- Root `/` redirects to docs

## Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/resolve` | Live conflict arbitration (IDE agents) |
| POST | `/resolve/demo/{name}` | Hackathon demo scenarios |
| POST | `/intents` | Record agent intent |
| POST | `/guardrails/check` | Pre-write check (agentic workflow; JSON body) |
| POST | `/guardrail/check` | Hackathon demo: proactive cache-delete scenario |
| GET | `/conflicts` | List conflicts for dashboard |
| GET | `/conflicts/{id}` | Conflict detail |
| POST | `/conflicts/{id}/approve` | Human approve/reject |
| GET | `/history?session_id=` | Session event log |
| WS | `/ws/conflicts?session_id=` | Live conflict stream |

## Dashboard

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 — proxies `/api` and `/ws` to the backend.

## MCP (Cursor / Claude Code)

```bash
pip install mcp
cd overlord && python mcp/server.py
```

Add to Cursor MCP config (stdio): command `python`, args `mcp/server.py`, cwd `overlord/`.

Tools: `overlord_declare_intent`, `overlord_guardrail_check`, `overlord_resolve_conflict`, `overlord_get_history`.

## Claude Code hook

```bash
chmod +x integrations/claude-code/pre-write.sh
export OVERLORD_SESSION_ID=your_session
# Wire script in Claude Code PreToolUse for Write/Edit
```

## E2E demo

```bash
chmod +x scripts/e2e_agentic_demo.sh
OVERLORD_MOCK_BEDROCK=1 ./scripts/e2e_agentic_demo.sh
```

## Tests

```bash
pytest backend/tests -v
```
