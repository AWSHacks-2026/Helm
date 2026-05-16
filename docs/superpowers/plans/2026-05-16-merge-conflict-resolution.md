# Merge Conflict Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Overlord’s merge-conflict arbitration path — Bedrock client, `arbitrate()` with merge-specific prompting, JSON response shaping, and an end-to-end `POST /resolve/merge_conflict` demo using the PRD’s cache-vs-readability scenario.

**Architecture:** Python 3.11 FastAPI backend under `overlord/backend/`. Person 1 owns `bedrock/client.py` and `overlord.py` (Bedrock `invoke_model` + merge prompt). Minimal `agents/scenarios.py` and `main.py` stubs are included only so this slice is demoable before Person 2 finishes the full scenario/simulator work. Bedrock Sonnet 4 performs one-shot structural merge; Haiku is out of scope for this plan. Knowledge Base reads are optional hooks (Person 3); merge resolution works without KB for hackathon critical path.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, boto3, python-dotenv, pytest, pytest-asyncio, httpx (TestClient)

**PRD references:** Feature 1 (§4), API contract (§5.3), scaffolding (§5.5), Person 1 work split (§6)

---

## File structure

| File | Responsibility |
|------|----------------|
| `overlord/backend/bedrock/client.py` | boto3 `bedrock-runtime` + `bedrock-agent-runtime` factories |
| `overlord/backend/bedrock/__init__.py` | Package marker |
| `overlord/backend/overlord.py` | `arbitrate()`, merge prompt, JSON parse/validate |
| `overlord/backend/models.py` | Pydantic types for agent payloads and resolution |
| `overlord/backend/agents/scenarios.py` | `merge_conflict` scenario data (minimal; Person 2 expands later) |
| `overlord/backend/agents/__init__.py` | Package marker |
| `overlord/backend/main.py` | FastAPI routes: `GET /scenarios`, `POST /resolve/{name}` |
| `overlord/backend/tests/test_client.py` | Client factory tests |
| `overlord/backend/tests/test_overlord.py` | `arbitrate()` unit tests (mocked Bedrock) |
| `overlord/backend/tests/test_resolve_merge.py` | HTTP integration test for merge scenario |
| `overlord/requirements.txt` | Runtime + dev dependencies |
| `overlord/.env.example` | Document required env vars (no secrets) |
| `overlord/pytest.ini` | pytest pythonpath |

**Out of scope (other owners):** `bedrock/knowledge_base.py`, `bedrock/guardrails.py`, `agents/simulator.py`, intent/dependency scenarios, frontend, token counter UI.

---

### Task 1: Project scaffolding

**Files:**
- Create: `overlord/requirements.txt`
- Create: `overlord/pytest.ini`
- Create: `overlord/.env.example`
- Create: `overlord/backend/__init__.py`

- [ ] **Step 1: Create requirements**

```text
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
boto3>=1.35.0
python-dotenv>=1.0.0
pydantic>=2.9.0
pytest>=8.3.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
```

- [ ] **Step 2: Create pytest config**

```ini
[pytest]
pythonpath = backend
testpaths = backend/tests
asyncio_mode = auto
```

- [ ] **Step 3: Create env example**

```bash
# Copy to overlord/.env and fill in after AWS setup (PRD §9)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
# Optional: skip real Bedrock in manual smoke tests
OVERLORD_MOCK_BEDROCK=0
```

- [ ] **Step 4: Install and verify**

Run from repo root:

```bash
cd overlord
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c "import fastapi, boto3; print('ok')"
```

Expected: prints `ok`

- [ ] **Step 5: Commit**

```bash
git add overlord/requirements.txt overlord/pytest.ini overlord/.env.example overlord/backend/__init__.py
git commit -m "chore: scaffold overlord backend for merge conflict slice"
```

---

### Task 2: Response models

**Files:**
- Create: `overlord/backend/models.py`
- Test: `overlord/backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `overlord/backend/tests/test_models.py`:

```python
from models import AgentPayload, ResolutionPayload, ResolveResponse


def test_resolution_payload_requires_merge_fields():
    r = ResolutionPayload(
        conflict_type="merge_conflict",
        reasoning="Merged cache and type hints.",
        resolved_code="def get_user(user_id: str) -> User: ...",
        tokens_saved_estimate="~2400",
    )
    assert r.conflict_type == "merge_conflict"


def test_resolve_response_shape():
    resp = ResolveResponse(
        agent_a=AgentPayload(intent="a", code="code_a"),
        agent_b=AgentPayload(intent="b", code="code_b"),
        resolution=ResolutionPayload(
            conflict_type="merge_conflict",
            reasoning="r",
            resolved_code="merged",
            tokens_saved_estimate="100",
        ),
    )
    assert resp.agent_a.intent == "a"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd overlord && source .venv/bin/activate
pytest backend/tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Implement models**

Create `overlord/backend/models.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field


class AgentPayload(BaseModel):
    intent: str
    code: str


class ResolutionPayload(BaseModel):
    conflict_type: Literal[
        "merge_conflict", "intent_conflict", "dependency_conflict"
    ]
    reasoning: str
    resolved_code: str
    tokens_saved_estimate: str


class ResolveResponse(BaseModel):
    agent_a: AgentPayload
    agent_b: AgentPayload
    resolution: ResolutionPayload


class BedrockArbitrationResult(BaseModel):
    """Raw JSON shape we ask Sonnet to return."""

    conflict_type: str
    reasoning: str
    resolved_code: str
    tokens_saved_estimate: str
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/test_models.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add overlord/backend/models.py overlord/backend/tests/test_models.py
git commit -m "feat: add pydantic models for merge conflict API contract"
```

---

### Task 3: Bedrock client factory

**Files:**
- Create: `overlord/backend/bedrock/__init__.py`
- Create: `overlord/backend/bedrock/client.py`
- Test: `overlord/backend/tests/test_client.py`

- [ ] **Step 1: Write the failing test**

Create `overlord/backend/tests/test_client.py`:

```python
from unittest.mock import MagicMock, patch

from bedrock.client import get_bedrock_agent_client, get_bedrock_client


@patch("bedrock.client.boto3.client")
def test_get_bedrock_client_uses_runtime_and_region(mock_boto_client):
    mock_boto_client.return_value = MagicMock()
    client = get_bedrock_client()
    mock_boto_client.assert_called_once_with(
        service_name="bedrock-runtime",
        region_name="us-east-1",
    )
    assert client is mock_boto_client.return_value


@patch("bedrock.client.boto3.client")
def test_get_bedrock_agent_client_uses_agent_runtime(mock_boto_client):
    mock_boto_client.return_value = MagicMock()
    client = get_bedrock_agent_client()
    mock_boto_client.assert_called_once_with(
        service_name="bedrock-agent-runtime",
        region_name="us-east-1",
    )
    assert client is mock_boto_client.return_value
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_client.py -v
```

Expected: FAIL — cannot import `bedrock.client`

- [ ] **Step 3: Implement client**

Create `overlord/backend/bedrock/__init__.py` (empty).

Create `overlord/backend/bedrock/client.py`:

```python
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


def get_bedrock_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=REGION,
    )


def get_bedrock_agent_client():
    return boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=REGION,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/test_client.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add overlord/backend/bedrock/ overlord/backend/tests/test_client.py
git commit -m "feat: add Bedrock boto3 client factories"
```

---

### Task 4: JSON extraction helper

**Files:**
- Create: `overlord/backend/overlord_parse.py`
- Test: `overlord/backend/tests/test_overlord_parse.py`

Models sometimes wrap JSON in markdown fences. Isolate parsing for testability.

- [ ] **Step 1: Write the failing test**

Create `overlord/backend/tests/test_overlord_parse.py`:

```python
import pytest

from overlord_parse import extract_json_object


def test_extract_json_object_plain():
    raw = '{"conflict_type": "merge_conflict", "resolved_code": "x"}'
    assert extract_json_object(raw)["conflict_type"] == "merge_conflict"


def test_extract_json_object_from_markdown_fence():
    raw = """Here is the result:
```json
{"conflict_type": "merge_conflict", "resolved_code": "x"}
```
"""
    assert extract_json_object(raw)["resolved_code"] == "x"


def test_extract_json_object_raises_on_garbage():
    with pytest.raises(ValueError):
        extract_json_object("not json at all")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_overlord_parse.py -v
```

Expected: FAIL — `No module named 'overlord_parse'`

- [ ] **Step 3: Implement parser**

Create `overlord/backend/overlord_parse.py`:

```python
import json
import re
from typing import Any


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fence_match = _FENCE_RE.search(stripped)
    if fence_match:
        stripped = fence_match.group(1).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")

    return json.loads(stripped[start : end + 1])
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/test_overlord_parse.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add overlord/backend/overlord_parse.py overlord/backend/tests/test_overlord_parse.py
git commit -m "feat: parse Sonnet JSON from plain or fenced output"
```

---

### Task 5: Merge-conflict prompt builder

**Files:**
- Create: `overlord/backend/overlord_prompt.py`
- Test: `overlord/backend/tests/test_overlord_prompt.py`

- [ ] **Step 1: Write the failing test**

Create `overlord/backend/tests/test_overlord_prompt.py`:

```python
from overlord_prompt import build_merge_conflict_prompt


def test_build_merge_conflict_prompt_includes_both_intents_and_code():
    prompt = build_merge_conflict_prompt(
        agent_a={"intent": "speed via cache", "code": "def get_user(): pass"},
        agent_b={"intent": "readability", "code": "def get_user(user_id: str): pass"},
    )
    assert "speed via cache" in prompt
    assert "readability" in prompt
    assert "def get_user(): pass" in prompt
    assert "def get_user(user_id: str): pass" in prompt
    assert "merge_conflict" in prompt
    assert "resolved_code" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_overlord_prompt.py -v
```

Expected: FAIL — import error

- [ ] **Step 3: Implement prompt builder**

Create `overlord/backend/overlord_prompt.py`:

```python
import json


def build_merge_conflict_prompt(agent_a: dict, agent_b: dict) -> str:
    schema = {
        "conflict_type": "merge_conflict",
        "reasoning": "string — why you merged this way and what you prioritized",
        "resolved_code": "string — single unified code output",
        "tokens_saved_estimate": "string — e.g. '~2400 tokens saved vs two agents fixing independently'",
    }

    return f"""You are Overlord, a supervisor agent resolving MERGE CONFLICTS between two AI coding agents.

Both agents edited the same function or file in incompatible ways. Your job:
1. Compare the structural differences (signatures, control flow, imports, side effects).
2. Produce ONE unified version that satisfies both agents' stated intents where possible.
3. Prefer combining complementary changes (e.g. caching AND type hints) over picking one side.
4. If intents truly conflict, explain the tradeoff and choose the safer default for production code.
5. Set conflict_type to exactly "merge_conflict".

Agent A intent: {agent_a["intent"]}

Agent A code:
{agent_a["code"]}

Agent B intent: {agent_b["intent"]}

Agent B code:
{agent_b["code"]}

Respond ONLY with a single JSON object matching this schema (no markdown, no preamble):
{json.dumps(schema, indent=2)}
"""
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/test_overlord_prompt.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add overlord/backend/overlord_prompt.py overlord/backend/tests/test_overlord_prompt.py
git commit -m "feat: add merge-conflict arbitration prompt builder"
```

---

### Task 6: `arbitrate()` with mocked Bedrock

**Files:**
- Create: `overlord/backend/overlord.py`
- Test: `overlord/backend/tests/test_overlord.py`

- [ ] **Step 1: Write the failing test**

Create `overlord/backend/tests/test_overlord.py`:

```python
import json
from unittest.mock import MagicMock, patch

from overlord import OVERLORD_MODEL, arbitrate


def _bedrock_body(text: str) -> dict:
    return {
        "content": [{"type": "text", "text": text}],
    }


@patch("overlord.get_bedrock_client")
def test_arbitrate_returns_parsed_resolution(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    model_json = json.dumps(
        {
            "conflict_type": "merge_conflict",
            "reasoning": "Kept cache and type hints.",
            "resolved_code": "def get_user(user_id: str) -> User:\n    ...",
            "tokens_saved_estimate": "~2400",
        }
    )
    mock_client.invoke_model.return_value = {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps(_bedrock_body(model_json)).encode()
            )
        )
    }

    result = arbitrate(
        agent_a={"intent": "cache", "code": "def get_user(user_id): ..."},
        agent_b={"intent": "types", "code": "def get_user(user_id: str) -> User: ..."},
    )

    assert result["conflict_type"] == "merge_conflict"
    assert "cache" in result["reasoning"].lower() or "type" in result["reasoning"].lower()
    assert "get_user" in result["resolved_code"]

    mock_client.invoke_model.assert_called_once()
    call_kwargs = mock_client.invoke_model.call_args.kwargs
    assert call_kwargs["modelId"] == OVERLORD_MODEL
    body = json.loads(call_kwargs["body"])
    assert body["anthropic_version"] == "bedrock-2023-05-31"
    assert body["max_tokens"] >= 1000
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_overlord.py -v
```

Expected: FAIL — cannot import `overlord`

- [ ] **Step 3: Implement `arbitrate()`**

Create `overlord/backend/overlord.py`:

```python
import json
import os
from typing import Any

from bedrock.client import get_bedrock_client
from models import BedrockArbitrationResult
from overlord_parse import extract_json_object
from overlord_prompt import build_merge_conflict_prompt

OVERLORD_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"
MAX_TOKENS = 1500


def arbitrate(agent_a: dict, agent_b: dict, kb_context: str | None = None) -> dict[str, Any]:
    """Call Sonnet via Bedrock to resolve a merge conflict between two agents."""
    client = get_bedrock_client()
    prompt = build_merge_conflict_prompt(agent_a, agent_b)
    if kb_context:
        prompt += f"\n\nRelevant history from Knowledge Base:\n{kb_context}"

    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        return _mock_merge_resolution()

    response = client.invoke_model(
        modelId=OVERLORD_MODEL,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )

    payload = json.loads(response["body"].read())
    text = payload["content"][0]["text"]
    raw = extract_json_object(text)
    validated = BedrockArbitrationResult.model_validate(raw)
    return validated.model_dump()


def _mock_merge_resolution() -> dict[str, Any]:
    return {
        "conflict_type": "merge_conflict",
        "reasoning": "MOCK: Combined Agent A caching with Agent B type hints.",
        "resolved_code": (
            "def get_user(user_id: str) -> User:\n"
            "    if user_id in cache:\n"
            "        return cache[user_id]\n"
            "    result = db.query(user_id)\n"
            "    cache[user_id] = result\n"
            "    return result\n"
        ),
        "tokens_saved_estimate": "~2400 (mock)",
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/test_overlord.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add overlord/backend/overlord.py overlord/backend/tests/test_overlord.py
git commit -m "feat: implement arbitrate() for merge conflicts via Bedrock Sonnet"
```

---

### Task 7: Merge conflict scenario data

**Files:**
- Create: `overlord/backend/agents/__init__.py`
- Create: `overlord/backend/agents/scenarios.py`
- Test: `overlord/backend/tests/test_scenarios.py`

Person 2 will add `intent_conflict` and `dependency_conflict` later. This task only defines `merge_conflict`.

- [ ] **Step 1: Write the failing test**

Create `overlord/backend/tests/test_scenarios.py`:

```python
from agents.scenarios import SCENARIOS


def test_merge_conflict_scenario_exists_with_required_keys():
    scenario = SCENARIOS["merge_conflict"]
    assert "agent_a" in scenario
    assert "agent_b" in scenario
    assert scenario["agent_a"]["intent"]
    assert "cache" in scenario["agent_a"]["intent"].lower()
    assert "get_user" in scenario["agent_a"]["code"]
    assert "get_user" in scenario["agent_b"]["code"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_scenarios.py -v
```

Expected: FAIL — import error

- [ ] **Step 3: Add scenario**

Create `overlord/backend/agents/__init__.py` (empty).

Create `overlord/backend/agents/scenarios.py`:

```python
SCENARIOS = {
    "merge_conflict": {
        "agent_a": {
            "intent": "I am optimizing this function for speed using caching",
            "code": """
def get_user(user_id):
    if user_id in cache:
        return cache[user_id]
    result = db.query(user_id)
    cache[user_id] = result
    return result
""".strip(),
        },
        "agent_b": {
            "intent": "I am refactoring this function for readability and adding type hints",
            "code": """
def get_user(user_id: str) -> User:
    return db.query(user_id)
""".strip(),
        },
    },
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/test_scenarios.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add overlord/backend/agents/ overlord/backend/tests/test_scenarios.py
git commit -m "feat: add merge_conflict demo scenario from PRD"
```

---

### Task 8: FastAPI resolve route

**Files:**
- Create: `overlord/backend/main.py`
- Test: `overlord/backend/tests/test_resolve_merge.py`

- [ ] **Step 1: Write the failing integration test**

Create `overlord/backend/tests/test_resolve_merge.py`:

```python
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ["OVERLORD_MOCK_BEDROCK"] = "1"

from main import app  # noqa: E402


client = TestClient(app)


def test_get_scenarios_lists_merge_conflict():
    response = client.get("/scenarios")
    assert response.status_code == 200
    assert "merge_conflict" in response.json()


@patch("main.arbitrate")
def test_resolve_merge_conflict_returns_api_contract(mock_arbitrate):
    mock_arbitrate.return_value = {
        "conflict_type": "merge_conflict",
        "reasoning": "Merged cache and types.",
        "resolved_code": "def get_user(user_id: str) -> User: ...",
        "tokens_saved_estimate": "~2400",
    }

    response = client.post("/resolve/merge_conflict")
    assert response.status_code == 200
    body = response.json()
    assert body["agent_a"]["intent"]
    assert body["agent_b"]["intent"]
    assert body["resolution"]["conflict_type"] == "merge_conflict"
    assert body["resolution"]["resolved_code"]
    mock_arbitrate.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_resolve_merge.py -v
```

Expected: FAIL — cannot import `main`

- [ ] **Step 3: Implement FastAPI app**

Create `overlord/backend/main.py`:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.scenarios import SCENARIOS
from models import AgentPayload, ResolutionPayload, ResolveResponse
from overlord import arbitrate

app = FastAPI(title="Overlord", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/scenarios")
def get_scenarios() -> list[str]:
    return list(SCENARIOS.keys())


@app.post("/resolve/{scenario_name}", response_model=ResolveResponse)
def resolve_conflict(scenario_name: str) -> ResolveResponse:
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scenario = SCENARIOS[scenario_name]
    agent_a = AgentPayload.model_validate(scenario["agent_a"])
    agent_b = AgentPayload.model_validate(scenario["agent_b"])

    raw_resolution = arbitrate(
        agent_a.model_dump(),
        agent_b.model_dump(),
    )
    resolution = ResolutionPayload.model_validate(raw_resolution)

    return ResolveResponse(
        agent_a=agent_a,
        agent_b=agent_b,
        resolution=resolution,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/test_resolve_merge.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add overlord/backend/main.py overlord/backend/tests/test_resolve_merge.py
git commit -m "feat: expose POST /resolve/merge_conflict and GET /scenarios"
```

---

### Task 9: Live Bedrock smoke test (manual)

**Files:** none (manual verification)

- [ ] **Step 1: Configure AWS**

Follow PRD §9: Bedrock model access for Sonnet 4, `aws configure`, copy `overlord/.env.example` → `overlord/.env`.

- [ ] **Step 2: Run server without mock**

```bash
cd overlord && source .venv/bin/activate
unset OVERLORD_MOCK_BEDROCK
cd backend && uvicorn main:app --reload --port 8000
```

- [ ] **Step 3: Call resolve endpoint**

```bash
curl -s -X POST http://localhost:8000/resolve/merge_conflict | python -m json.tool
```

Expected:
- HTTP 200
- `resolution.conflict_type` == `"merge_conflict"`
- `resolution.resolved_code` contains both caching logic and type hints (`user_id: str`, `-> User` or equivalent)
- `resolution.reasoning` explains the merge
- `resolution.tokens_saved_estimate` is a non-empty string

- [ ] **Step 4: Record real token estimate for demo**

Note `max_tokens` and actual usage from CloudWatch or response metadata if available; update demo copy per PRD §7.2 (prefer real counts over guesses).

- [ ] **Step 5: Commit** (only if you add a small `overlord/README.md` with run instructions — optional)

---

### Task 10: Optional KB context hook (integration point for Person 3)

**Files:**
- Modify: `overlord/backend/overlord.py`
- Modify: `overlord/backend/main.py`

Skip if Person 3’s KB is not ready. Merge resolution must work with `kb_context=None`.

- [ ] **Step 1: Add stub KB reader**

When `bedrock/knowledge_base.py` exists, `main.py` should call:

```python
# In resolve_conflict(), before arbitrate():
kb_context = None
try:
    from bedrock.knowledge_base import get_context_for_agents
    kb_context = get_context_for_agents(["agent_a", "agent_b"], module_hint="get_user")
except ImportError:
    pass

raw_resolution = arbitrate(agent_a.model_dump(), agent_b.model_dump(), kb_context=kb_context)
```

No test required until Person 3 lands the module; document the contract in a code comment.

- [ ] **Step 2: Commit** (when wired)

```bash
git commit -m "feat: optional KB context passthrough for merge arbitration"
```

---

## Self-review

### 1. Spec coverage (PRD Feature 1 + Person 1 scope)

| PRD requirement | Plan task |
|-----------------|-----------|
| Two agents produce incompatible diffs | Task 7 — `merge_conflict` scenario |
| Overlord receives versions + intents | Task 5–6 — prompt + `arbitrate()` |
| Sonnet analyzes structural diff, unified resolution | Task 5–6 — merge-specific prompt |
| JSON: `conflict_type`, `reasoning`, `resolved_code`, `tokens_saved_estimate` | Tasks 2, 6 |
| `invoke_model` to Sonnet | Task 6 |
| Demo: cache vs readability | Tasks 7–9 |
| `bedrock/client.py` | Task 3 |
| `overlord.py` / `arbitrate()` | Task 6 |
| API `POST /resolve/{scenario}` | Task 8 |
| KB informs resolution | Task 10 (optional hook) |

**Gaps:** Real token counter UI (Person 2/frontend), Haiku sub-agent simulation (out of merge slice), proactive guardrails (Person 3).

### 2. Placeholder scan

No TBD steps. All code blocks are complete. Commands and expected outputs specified.

### 3. Type consistency

- API uses `resolved_code` (not PRD scaffold’s erroneous `"resolution"` field in JSON).
- `conflict_type` for this feature is always `"merge_conflict"`.
- `AgentPayload` / `ResolutionPayload` used consistently in `main.py` and tests.

---

## Merge order note (team)

Per PRD §6: Person 1 lands first (`bedrock/client.py`, `overlord.py`). Person 3 adds `bedrock/knowledge_base.py` and `guardrails.py` without touching `overlord_prompt.py`. Person 2 expands `scenarios.py`, adds `simulator.py`, token counter — coordinate on `main.py` imports to avoid conflicts.

---

## Execution handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-16-merge-conflict-resolution.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
