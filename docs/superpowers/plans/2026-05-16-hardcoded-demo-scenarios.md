# Hardcoded Demo Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship three PRD hardcoded scenarios (merge conflict, intent conflict, guardrail prevention) with one-shot API paths and a `/demo/smoke` health check so the team can verify all three acts work locally with `HELM_MOCK_BEDROCK=1`.

**Architecture:** Extend `helm/backend/agents/scenarios.py` with a typed scenario registry (`kind`: `merge` | `intent` | `guardrail`). Merge and intent scenarios use `POST /resolve/{name}` with scenario-specific prompts in `helm_prompt.py`. Guardrail uses existing `POST /guardrail/check` (seeds KB, runs preflight, routes to Helm). Add `GET /demo/smoke` that runs all three paths and returns pass/fail JSON for Swagger and curl. No frontend required.

**Tech Stack:** Python 3.11, FastAPI, pytest, httpx TestClient, existing `helm.py` + `guardrails.py` + `knowledge_base.py`

**PRD references:** Feature 1–3 demo scenarios (§4), API contract (§5.3), three-act demo (§7.1)

---

## File map

| File | Responsibility |
|------|----------------|
| `helm/backend/agents/scenarios.py` | All hardcoded scenario payloads + `SCENARIO_META` |
| `helm/backend/helm_prompt.py` | `build_intent_conflict_prompt`, `build_guardrail_resolution_prompt` |
| `helm/backend/helm.py` | Route `arbitrate()` to correct prompt by `conflict_type` or scenario name |
| `helm/backend/main.py` | `GET /`, `GET /demo/smoke`, wire resolve with scenario kind |
| `helm/backend/tests/test_scenarios.py` | Assert all three scenarios exist |
| `helm/backend/tests/test_demo_smoke.py` | HTTP smoke for `/demo/smoke` |
| `helm/README.md` | How to run demo smoke + per-act curl commands |

**Already exists (do not rewrite):**

- `merge_conflict` scenario + merge prompt
- `GUARDRAIL_DEMO_SCENARIO` + `seed_guardrail_demo()` + `POST /guardrail/check`
- Guardrail preflight rules in `bedrock/guardrails.py`

---

### Task 1: Scenario registry + intent_conflict payload

**Files:**
- Modify: `helm/backend/agents/scenarios.py`
- Modify: `helm/backend/tests/test_scenarios.py`

- [ ] **Step 1: Write failing tests**

```python
# helm/backend/tests/test_scenarios.py
from agents.scenarios import SCENARIOS, SCENARIO_META


def test_all_three_demo_scenarios_registered():
    assert set(SCENARIOS.keys()) >= {
        "merge_conflict",
        "intent_conflict",
        "guardrail_prevention",
    }


def test_scenario_meta_kinds():
    assert SCENARIO_META["merge_conflict"]["kind"] == "merge"
    assert SCENARIO_META["intent_conflict"]["kind"] == "intent"
    assert SCENARIO_META["guardrail_prevention"]["kind"] == "guardrail"


def test_intent_conflict_scenario_from_prd():
    s = SCENARIOS["intent_conflict"]
    assert "performance" in s["agent_a"]["intent"].lower()
    assert "dependenc" in s["agent_b"]["intent"].lower()
    assert s["agent_a"]["code"]
    assert s["agent_b"]["code"]
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd helm && source .venv/bin/activate && pytest backend/tests/test_scenarios.py -v`

Expected: `KeyError: 'intent_conflict'` or missing `SCENARIO_META`

- [ ] **Step 3: Implement scenarios**

Replace `helm/backend/agents/scenarios.py` with:

```python
from bedrock.guardrails import GUARDRAIL_DEMO_SCENARIO

# kind drives prompt selection in helm.arbitrate()
SCENARIO_META: dict[str, dict[str, str]] = {
    "merge_conflict": {
        "kind": "merge",
        "title": "Act 1 — Cache vs readability (get_user)",
        "description": "Two agents edited the same function differently.",
    },
    "intent_conflict": {
        "kind": "intent",
        "title": "Act 2 — Performance vs minimal dependencies",
        "description": "Contradictory goals before code diverges.",
    },
    "guardrail_prevention": {
        "kind": "guardrail",
        "title": "Act 3 — Block delete of peer's cache utility",
        "description": "Use POST /guardrail/check (not /resolve) for full flow.",
    },
}

SCENARIOS: dict[str, dict] = {
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
    "intent_conflict": {
        "agent_a": {
            "intent": "I am optimizing this module for maximum performance",
            "code": """
# module: data_access.py
# Plan: add in-memory cache + connection pooling for all DB reads
CACHE_TTL = 300
_pool = None

def get_user(user_id: str):
    return _cached_fetch("user", user_id)
""".strip(),
        },
        "agent_b": {
            "intent": "I am refactoring this module to minimize dependencies",
            "code": """
# module: data_access.py
# Plan: remove cache layer and third-party pool; use stdlib only
import sqlite3

def get_user(user_id: str):
    with sqlite3.connect("app.db") as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
""".strip(),
        },
    },
    "guardrail_prevention": {
        "agent_a": GUARDRAIL_DEMO_SCENARIO["agent_a"],
        "agent_b": GUARDRAIL_DEMO_SCENARIO["agent_b"],
    },
}


def get_scenario_kind(name: str) -> str:
    return SCENARIO_META[name]["kind"]
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest backend/tests/test_scenarios.py -v`

Expected: `4 passed` (including existing merge test if updated)

- [ ] **Step 5: Commit**

```bash
git add helm/backend/agents/scenarios.py helm/backend/tests/test_scenarios.py
git commit -m "feat(scenarios): register merge, intent, and guardrail demo scenarios"
```

---

### Task 2: Intent + guardrail arbitration prompts

**Files:**
- Modify: `helm/backend/helm_prompt.py`
- Create: `helm/backend/tests/test_helm_prompt_intent.py`

- [ ] **Step 1: Write failing tests**

```python
# helm/backend/tests/test_helm_prompt_intent.py
from helm_prompt import (
    build_guardrail_resolution_prompt,
    build_intent_conflict_prompt,
)


def test_build_intent_conflict_prompt_mentions_both_intents():
    prompt = build_intent_conflict_prompt(
        agent_a={"intent": "max performance", "code": "# a"},
        agent_b={"intent": "min dependencies", "code": "# b"},
    )
    assert "max performance" in prompt
    assert "min dependencies" in prompt
    assert "intent_conflict" in prompt


def test_build_guardrail_resolution_prompt_mentions_block():
    prompt = build_guardrail_resolution_prompt(
        agent_a={"intent": "keep cache", "code": "# keep"},
        agent_b={"intent": "delete cache", "code": "# delete"},
        proposed_action={"description": "Remove caching utility"},
        rule="reverses_recent_decision",
    )
    assert "reverses_recent_decision" in prompt
    assert "Remove caching utility" in prompt
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest backend/tests/test_helm_prompt_intent.py -v`

- [ ] **Step 3: Append to helm_prompt.py**

```python
def build_intent_conflict_prompt(agent_a: dict, agent_b: dict) -> str:
    schema = {
        "conflict_type": "intent_conflict",
        "reasoning": "string — why these intents conflict and how you compromised",
        "resolved_code": "string — unified intent directive BOTH agents should follow (2-4 sentences); may include short code sketch",
        "tokens_saved_estimate": "string — e.g. '~1800 tokens saved vs agents looping on goals'",
    }
    return f"""You are Helm, resolving INTENT CONFLICTS between two AI coding agents.

The agents have NOT necessarily edited the same lines yet, but their stated goals contradict.
Your job:
1. Explain the incompatibility between Agent A and Agent B intents.
2. Produce ONE compromise directive both agents can follow before writing more code.
3. Prefer performance where it does not add dependencies; prefer native/stdlib over new packages.
4. Set conflict_type to exactly "intent_conflict".

Agent A intent: {agent_a["intent"]}

Agent A planned code:
{agent_a["code"]}

Agent B intent: {agent_b["intent"]}

Agent B planned code:
{agent_b["code"]}

Respond ONLY with a single JSON object matching this schema (no markdown, no preamble):
{json.dumps(schema, indent=2)}
"""


def build_guardrail_resolution_prompt(
    agent_a: dict,
    agent_b: dict,
    proposed_action: dict,
    rule: str,
    message: str,
) -> str:
    schema = {
        "conflict_type": "proactive_guardrail",
        "reasoning": "string — why the guardrail tripped and your verdict",
        "resolved_code": "string — what Agent B should do instead (e.g. refactor around cache)",
        "tokens_saved_estimate": "string",
        "verdict": "modify | block | allow_with_changes",
    }
    return f"""You are Helm. A proactive guardrail BLOCKED an agent action before execution.

Guardrail rule: {rule}
Guardrail message: {message}

Proposed action: {json.dumps(proposed_action, indent=2)}

Agent A intent: {agent_a.get("intent", "")}
Agent A code context: {agent_a.get("code", "")}

Agent B intent: {agent_b.get("intent", "")}
Agent B code context: {agent_b.get("code", "")}

Decide how Agent B should proceed. Set conflict_type to "proactive_guardrail".
Respond ONLY with JSON matching:
{json.dumps(schema, indent=2)}
"""
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest backend/tests/test_helm_prompt_intent.py -v`

- [ ] **Step 5: Commit**

```bash
git add helm/backend/helm_prompt.py helm/backend/tests/test_helm_prompt_intent.py
git commit -m "feat(helm): intent and guardrail arbitration prompts"
```

---

### Task 3: Route `arbitrate()` by scenario kind + mock responses

**Files:**
- Modify: `helm/backend/helm.py`
- Modify: `helm/backend/tests/test_helm.py`

- [ ] **Step 1: Write failing test**

```python
# Append to helm/backend/tests/test_helm.py
def test_arbitrate_intent_conflict_mock():
    import os
    os.environ["HELM_MOCK_BEDROCK"] = "1"
    from helm import arbitrate

    result = arbitrate(
        {"intent": "max performance", "code": "# a"},
        {"intent": "min dependencies", "code": "# b"},
        conflict_kind="intent",
    )
    assert result["conflict_type"] == "intent_conflict"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest backend/tests/test_helm.py::test_arbitrate_intent_conflict_mock -v`

- [ ] **Step 3: Update helm.py**

Add parameter `conflict_kind: str = "merge"` to `arbitrate()`.

When `HELM_MOCK_BEDROCK=1`:
- `merge` → existing `_mock_merge_resolution()`
- `intent` → return `conflict_type: intent_conflict`, reasoning mentions performance + dependencies
- `guardrail` → return `conflict_type: proactive_guardrail`, `verdict: modify`, resolved_code about refactoring around cache

When live Bedrock:
- `merge` → `build_merge_conflict_prompt`
- `intent` → `build_intent_conflict_prompt`
- `guardrail` → `build_guardrail_resolution_prompt` (requires extra kwargs: pass via `arbitrate(..., guardrail_context={...})`)

Parse with `BedrockArbitrationResult` but allow extra keys (`verdict`) via `model_validate` then `model_dump()` merged with raw dict for guardrail.

- [ ] **Step 4: Run helm tests — expect PASS**

Run: `pytest backend/tests/test_helm.py -v`

- [ ] **Step 5: Commit**

```bash
git add helm/backend/helm.py helm/backend/tests/test_helm.py
git commit -m "feat(helm): arbitrate by scenario kind with mock paths"
```

---

### Task 4: Wire resolve route + guardrail handler to scenario kinds

**Files:**
- Modify: `helm/backend/main.py`
- Modify: `helm/backend/bedrock/guardrails.py`
- Create: `helm/backend/tests/test_resolve_intent.py`

- [ ] **Step 1: Write failing HTTP test**

```python
# helm/backend/tests/test_resolve_intent.py
import os
from fastapi.testclient import TestClient

os.environ["HELM_MOCK_BEDROCK"] = "1"
from main import app  # noqa: E402

client = TestClient(app)


def test_resolve_intent_conflict_returns_intent_type():
    r = client.post("/resolve/intent_conflict")
    assert r.status_code == 200
    assert r.json()["resolution"]["conflict_type"] == "intent_conflict"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest backend/tests/test_resolve_intent.py -v`

- [ ] **Step 3: Update main.py resolve_conflict**

```python
from agents.scenarios import SCENARIOS, get_scenario_kind

# inside resolve_conflict, before arbitrate:
kind = get_scenario_kind(scenario_name)
if kind == "guardrail":
    raise HTTPException(
        status_code=400,
        detail="Use POST /guardrail/check for guardrail_prevention scenario",
    )

raw_resolution = arbitrate(
    agent_a.model_dump(),
    agent_b.model_dump(),
    kb_context=kb_context,
    conflict_kind=kind,
)
```

- [ ] **Step 4: Update guardrails.handle_proposed_action**

Change `_arbitrate` call to pass guardrail context:

```python
resolution = _arbitrate(
    agent_a,
    agent_b,
    kb_context=preflight.kb_context,
    conflict_kind="guardrail",
    guardrail_context={
        "proposed_action": proposed_action,
        "rule": preflight.rule or "",
        "message": preflight.message,
    },
)
```

Extend `arbitrate()` signature to accept optional `guardrail_context: dict | None`.

- [ ] **Step 5: Run tests — expect PASS**

Run: `pytest backend/tests/test_resolve_intent.py backend/tests/test_guardrails.py -v`

- [ ] **Step 6: Commit**

```bash
git add helm/backend/main.py helm/backend/bedrock/guardrails.py helm/backend/tests/test_resolve_intent.py
git commit -m "feat(api): resolve intent scenario; guardrail uses guardrail prompt"
```

---

### Task 5: `GET /demo/smoke` — one endpoint to verify all three acts

**Files:**
- Modify: `helm/backend/main.py`
- Create: `helm/backend/tests/test_demo_smoke.py`

- [ ] **Step 1: Write failing test**

```python
# helm/backend/tests/test_demo_smoke.py
import os
from fastapi.testclient import TestClient

os.environ["HELM_MOCK_BEDROCK"] = "1"
from main import app  # noqa: E402

client = TestClient(app)


def test_demo_smoke_all_pass():
    r = client.get("/demo/smoke")
    assert r.status_code == 200
    body = r.json()
    assert body["all_passed"] is True
    names = {c["scenario"] for c in body["checks"]}
    assert names == {"merge_conflict", "intent_conflict", "guardrail_prevention"}
    for check in body["checks"]:
        assert check["passed"] is True, check
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest backend/tests/test_demo_smoke.py -v`

- [ ] **Step 3: Implement smoke handler in main.py**

```python
@app.get("/")
def root():
    return {
        "service": "Helm",
        "docs": "/docs",
        "scenarios": "/scenarios",
        "demo_smoke": "/demo/smoke",
    }


@app.get("/demo/smoke")
def demo_smoke():
    """Run all three PRD demo paths with mock Bedrock; returns pass/fail checklist."""
    import os
    os.environ["HELM_MOCK_BEDROCK"] = "1"
    checks = []

    # Act 1 — merge
    try:
        scenario = SCENARIOS["merge_conflict"]
        raw = arbitrate(
            scenario["agent_a"],
            scenario["agent_b"],
            conflict_kind="merge",
        )
        ok = raw.get("conflict_type") == "merge_conflict" and "get_user" in raw.get(
            "resolved_code", ""
        )
        checks.append(
            {
                "scenario": "merge_conflict",
                "endpoint": "POST /resolve/merge_conflict",
                "passed": ok,
                "detail": raw.get("conflict_type"),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "scenario": "merge_conflict",
                "endpoint": "POST /resolve/merge_conflict",
                "passed": False,
                "detail": str(exc),
            }
        )

    # Act 2 — intent
    try:
        scenario = SCENARIOS["intent_conflict"]
        raw = arbitrate(
            scenario["agent_a"],
            scenario["agent_b"],
            conflict_kind="intent",
        )
        ok = raw.get("conflict_type") == "intent_conflict"
        checks.append(
            {
                "scenario": "intent_conflict",
                "endpoint": "POST /resolve/intent_conflict",
                "passed": ok,
                "detail": raw.get("conflict_type"),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "scenario": "intent_conflict",
                "passed": False,
                "detail": str(exc),
            }
        )

    # Act 3 — guardrail (isolated session)
    try:
        from pathlib import Path
        import tempfile

        session = Path(tempfile.mkdtemp()) / "smoke-session.json"
        os.environ["HELM_SESSION_PATH"] = str(session)
        result = guardrail_check()
        ok = (
            result["preflight"]["allowed"] is False
            and result["executed"] is False
            and result["resolution"] is not None
        )
        checks.append(
            {
                "scenario": "guardrail_prevention",
                "endpoint": "POST /guardrail/check",
                "passed": ok,
                "detail": result["preflight"].get("rule"),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "scenario": "guardrail_prevention",
                "passed": False,
                "detail": str(exc),
            }
        )

    return {
        "all_passed": all(c["passed"] for c in checks),
        "mock_bedrock": True,
        "checks": checks,
    }
```

Refactor `guardrail_check` body into a shared `_run_guardrail_demo()` returning dict so smoke and route do not duplicate logic.

- [ ] **Step 4: Run — expect PASS**

Run: `pytest backend/tests/test_demo_smoke.py -v`

- [ ] **Step 5: Commit**

```bash
git add helm/backend/main.py helm/backend/tests/test_demo_smoke.py
git commit -m "feat(api): GET /demo/smoke checklist for all three acts"
```

---

### Task 6: README + manual verification script

**Files:**
- Modify: `helm/README.md`

- [ ] **Step 1: Add Demo section to README**

```markdown
## Demo scenarios (three acts)

| Act | Scenario | How to run |
|-----|----------|------------|
| 1 | `merge_conflict` | `POST /resolve/merge_conflict` |
| 2 | `intent_conflict` | `POST /resolve/intent_conflict` |
| 3 | `guardrail_prevention` | `POST /guardrail/check` |

### Quick verify (mock Bedrock)

```bash
export HELM_MOCK_BEDROCK=1
cd backend && uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs or:

```bash
curl -s http://localhost:8000/demo/smoke | python3 -m json.tool
```

Expected: `"all_passed": true` and three checks with `"passed": true`.
```

- [ ] **Step 2: Manual run**

Run server + `curl http://localhost:8000/demo/smoke` — confirm `all_passed: true`

- [ ] **Step 3: Commit**

```bash
git add helm/README.md
git commit -m "docs: three-act demo scenarios and smoke endpoint"
```

---

### Task 7: Full test suite

- [ ] **Step 1: Run all tests**

Run: `cd helm && pytest backend/tests -v`

Expected: all passed (count increases by ~8–10 from new files)

- [ ] **Step 2: Commit** (only if fixes were needed)

---

## Self-review

### 1. Spec coverage

| PRD requirement | Task |
|-----------------|------|
| Act 1 merge demo (cache vs readability) | Task 1 (existing), Task 5 smoke |
| Act 2 intent demo (performance vs minimalism) | Task 1, 2, 3, 4 |
| Act 3 guardrail demo | Task 4, 5 (uses `/guardrail/check`) |
| `GET /scenarios` lists all | Task 1 |
| Verify “working good” without frontend | Task 5 `/demo/smoke` |
| API contract `conflict_type` values | Tasks 2–4 |

**Gaps:** `dependency_conflict` scenario deferred (not in PRD three-act demo). Frontend still separate.

### 2. Placeholder scan

No TBD steps. Code blocks are complete.

### 3. Type consistency

- `conflict_kind`: `"merge" | "intent" | "guardrail"` everywhere
- Guardrail HTTP path remains `POST /guardrail/check` (not `/resolve/guardrail_prevention`)
- `ResolutionPayload` still requires `resolved_code`; intent prompt uses directive string in that field

---

## Manual test cheatsheet (after implementation)

```bash
cd helm && source .venv/bin/activate
export HELM_MOCK_BEDROCK=1
cd backend && uvicorn main:app --reload --port 8000
```

| URL | Expected |
|-----|----------|
| http://localhost:8000/ | JSON with links to `/docs` and `/demo/smoke` |
| http://localhost:8000/demo/smoke | `"all_passed": true` |
| POST /resolve/merge_conflict | `conflict_type: merge_conflict` |
| POST /resolve/intent_conflict | `conflict_type: intent_conflict` |
| POST /guardrail/check | `preflight.allowed: false`, `executed: false` |

---

## Execution handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-16-hardcoded-demo-scenarios.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
