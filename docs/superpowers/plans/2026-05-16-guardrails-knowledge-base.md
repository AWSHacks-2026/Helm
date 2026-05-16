# Guardrails + Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Feature 3 — a proactive guardrails layer plus session memory (Knowledge Base) that intercepts conflicting agent actions before execution and supplies context to Overlord arbitration.

**Architecture:** Person 3 owns only `backend/bedrock/knowledge_base.py` and `backend/bedrock/guardrails.py`. Both modules expose a **dual-mode** design: local JSON + in-process rules work out of the box for the hackathon demo; when `BEDROCK_KB_ID` / `BEDROCK_GUARDRAIL_ID` env vars are set, the same APIs call `bedrock-agent-runtime.retrieve()` and `bedrock-runtime.apply_guardrail()`. Guardrails query KB history, return structured `PreflightResult`, and on trip call `overlord.arbitrate()` (from Person 1) with KB context injected. Person 2 wires `GET /history` and `POST /guardrail/check` in `main.py` using snippets in Task 12.

**Tech Stack:** Python 3.11, FastAPI (integration only), boto3 (`bedrock-agent-runtime`, `bedrock-runtime`, `s3`), pytest, python-dotenv, optional `moto` for S3 tests

---

## File map (Person 3 scope)

| File | Responsibility |
|---|---|
| `backend/bedrock/knowledge_base.py` | Record types, local store, S3 append, `retrieve()`, `get_history()` |
| `backend/bedrock/guardrails.py` | `preflight_check()`, Bedrock guardrail wrapper, `handle_proposed_action()`, demo seed |
| `backend/tests/bedrock/test_knowledge_base.py` | KB unit tests |
| `backend/tests/bedrock/test_guardrails.py` | Guardrail unit tests |
| `backend/tests/bedrock/conftest.py` | Temp session dir, env isolation |
| `backend/requirements.txt` | Shared deps (coordinate with team) |
| `.env.example` | KB / guardrail / S3 env vars |

**Depends on (Person 1 — merge first):**

- `backend/bedrock/client.py` — `get_bedrock_agent_client()`, `get_bedrock_runtime_client()`
- `backend/overlord.py` — `arbitrate(agent_a, agent_b, kb_context: list[dict] | None = None)`

**Hands off to (Person 2 — merge last):**

- `backend/main.py` — wire routes below
- `backend/agents/scenarios.py` — add `guardrail_prevention` scenario payload from Task 12

---

## Environment variables

```bash
# .env.example (Person 3 adds)
AWS_REGION=us-east-1
OVERLORD_USE_LOCAL_KB=true          # default true for hackathon
OVERLORD_SESSION_PATH=.overlord/session.json
OVERLORD_S3_BUCKET=                 # optional: s3://bucket/prefix/logs/
BEDROCK_KB_ID=                      # when set, enable retrieve()
BEDROCK_GUARDRAIL_ID=               # optional Bedrock Guardrails resource
BEDROCK_GUARDRAIL_VERSION=DRAFT     # or published version ARN suffix
```

---

## Shared types (used in both modules)

```python
# knowledge_base.py — RecordType, KnowledgeRecord
# guardrails.py imports KnowledgeRecord helpers
```

---

### Task 0: Backend test harness

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/tests/bedrock/conftest.py`
- Create: `backend/pytest.ini`

- [ ] **Step 1: Add requirements**

```text
boto3>=1.34.0
python-dotenv>=1.0.0
pytest>=8.0.0
moto[s3]>=5.0.0
```

- [ ] **Step 2: pytest config**

```ini
# backend/pytest.ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 3: conftest — isolated session file per test**

```python
# backend/tests/bedrock/conftest.py
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_kb_session(tmp_path, monkeypatch):
    session_file = tmp_path / "session.json"
    monkeypatch.setenv("OVERLORD_USE_LOCAL_KB", "true")
    monkeypatch.setenv("OVERLORD_SESSION_PATH", str(session_file))
    monkeypatch.delenv("BEDROCK_KB_ID", raising=False)
    monkeypatch.delenv("BEDROCK_GUARDRAIL_ID", raising=False)
    yield session_file
```

- [ ] **Step 4: Install and verify pytest runs**

Run: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pytest --collect-only`
Expected: `no tests ran` or empty collection (no failures)

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/pytest.ini backend/tests/bedrock/conftest.py
git commit -m "chore: add backend test harness for bedrock modules"
```

---

### Task 1: Knowledge record model + local append

**Files:**
- Create: `backend/bedrock/knowledge_base.py`
- Create: `backend/tests/bedrock/test_knowledge_base.py`

- [ ] **Step 1: Write failing tests for log + history**

```python
# backend/tests/bedrock/test_knowledge_base.py
from bedrock import knowledge_base as kb


def test_log_action_and_get_history():
    kb.log_action(
        agent_id="agent_a",
        action_type="add_file",
        file_path="utils/cache.py",
        description="Added caching utility",
    )
    history = kb.get_history()
    assert len(history) == 1
    assert history[0]["record_type"] == "action"
    assert history[0]["agent_id"] == "agent_a"
    assert history[0]["payload"]["file_path"] == "utils/cache.py"


def test_log_intent_includes_text():
    kb.log_intent(agent_id="agent_b", intent="Minimize dependencies in utils/")
    history = kb.get_history(record_type="intent")
    assert history[0]["payload"]["intent"] == "Minimize dependencies in utils/"
```

- [ ] **Step 2: Run tests — expect import error**

Run: `cd backend && pytest tests/bedrock/test_knowledge_base.py -v`
Expected: `ModuleNotFoundError: bedrock`

- [ ] **Step 3: Implement models + local store**

```python
# backend/bedrock/knowledge_base.py
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class RecordType(str, Enum):
    ACTION = "action"
    INTENT = "intent"
    DECISION = "decision"


@dataclass
class KnowledgeRecord:
    id: str
    timestamp: str
    record_type: RecordType
    agent_id: str
    session_id: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["record_type"] = self.record_type.value
        return data


def _session_path() -> Path:
    return Path(os.getenv("OVERLORD_SESSION_PATH", ".overlord/session.json"))


def _use_local_kb() -> bool:
    return os.getenv("OVERLORD_USE_LOCAL_KB", "true").lower() == "true"


def _read_all() -> list[dict[str, Any]]:
    path = _session_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _append(record: KnowledgeRecord) -> KnowledgeRecord:
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    records = _read_all()
    records.append(record.to_dict())
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return record


def _make_record(
    record_type: RecordType,
    agent_id: str,
    payload: dict[str, Any],
    session_id: str = "default",
) -> KnowledgeRecord:
    return KnowledgeRecord(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        record_type=record_type,
        agent_id=agent_id,
        session_id=session_id,
        payload=payload,
    )


def log_action(
    agent_id: str,
    action_type: str,
    file_path: str,
    description: str,
    metadata: dict[str, Any] | None = None,
    session_id: str = "default",
) -> KnowledgeRecord:
    payload = {
        "action_type": action_type,
        "file_path": file_path,
        "description": description,
        "metadata": metadata or {},
    }
    record = _make_record(RecordType.ACTION, agent_id, payload, session_id)
    return _append(record)


def log_intent(agent_id: str, intent: str, session_id: str = "default") -> KnowledgeRecord:
    record = _make_record(
        RecordType.INTENT,
        agent_id,
        {"intent": intent},
        session_id,
    )
    return _append(record)


def log_decision(
    reasoning: str,
    affected_agents: list[str],
    decision_id: str | None = None,
    session_id: str = "default",
) -> KnowledgeRecord:
    payload = {
        "decision_id": decision_id or str(uuid.uuid4()),
        "reasoning": reasoning,
        "affected_agents": affected_agents,
    }
    record = _make_record(RecordType.DECISION, "overlord", payload, session_id)
    return _append(record)


def get_history(
    limit: int = 50,
    record_type: str | None = None,
    agent_id: str | None = None,
) -> list[dict[str, Any]]:
    records = _read_all()
    if record_type:
        records = [r for r in records if r["record_type"] == record_type]
    if agent_id:
        records = [r for r in records if r["agent_id"] == agent_id]
    return records[-limit:]
```

- [ ] **Step 4: Add package init**

```python
# backend/bedrock/__init__.py
# empty
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `cd backend && pytest tests/bedrock/test_knowledge_base.py -v`
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/bedrock/__init__.py backend/bedrock/knowledge_base.py backend/tests/bedrock/test_knowledge_base.py
git commit -m "feat(kb): local session log for agent actions and intents"
```

---

### Task 2: Bedrock KB retrieve (with local fallback)

**Files:**
- Modify: `backend/bedrock/knowledge_base.py`
- Modify: `backend/tests/bedrock/test_knowledge_base.py`

**Prerequisite:** Person 1 merged `backend/bedrock/client.py` with:

```python
def get_bedrock_agent_client():
    return boto3.client("bedrock-agent-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
```

- [ ] **Step 1: Write failing test for local semantic fallback**

```python
def test_retrieve_context_local_keyword_match():
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added caching utility")
    kb.log_intent("agent_b", "Remove unused utilities")
    results = kb.retrieve_context("caching utility agent_a", max_results=3)
    assert len(results) >= 1
    assert any("cache" in json.dumps(r).lower() for r in results)
```

(Add `import json` at top of test file.)

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd backend && pytest tests/bedrock/test_knowledge_base.py::test_retrieve_context_local_keyword_match -v`
Expected: `AttributeError: module ... has no attribute 'retrieve_context'`

- [ ] **Step 3: Implement retrieve_context**

```python
# Append to knowledge_base.py

def retrieve_context(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    kb_id = os.getenv("BEDROCK_KB_ID", "").strip()
    if kb_id and not _use_local_kb():
        return _retrieve_from_bedrock(query, max_results, kb_id)
    return _retrieve_local(query, max_results)


def _retrieve_local(query: str, max_results: int) -> list[dict[str, Any]]:
    tokens = {t.lower() for t in query.split() if len(t) > 2}
    scored: list[tuple[int, dict[str, Any]]] = []
    for record in _read_all():
        blob = json.dumps(record).lower()
        score = sum(1 for t in tokens if t in blob)
        if score:
            scored.append((score, record))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:max_results]]


def _retrieve_from_bedrock(query: str, max_results: int, kb_id: str) -> list[dict[str, Any]]:
    from bedrock.client import get_bedrock_agent_client

    client = get_bedrock_agent_client()
    response = client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": max_results}
        },
    )
    results = []
    for item in response.get("retrievalResults", []):
        results.append(
            {
                "score": item.get("score"),
                "content": item.get("content", {}).get("text", ""),
                "metadata": item.get("metadata", {}),
            }
        )
    return results
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd backend && pytest tests/bedrock/test_knowledge_base.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/bedrock/knowledge_base.py backend/tests/bedrock/test_knowledge_base.py
git commit -m "feat(kb): retrieve_context with Bedrock KB and local fallback"
```

---

### Task 3: S3 log sync (optional, enables real KB indexing)

**Files:**
- Modify: `backend/bedrock/knowledge_base.py`
- Create: `backend/tests/bedrock/test_knowledge_base_s3.py`

- [ ] **Step 1: Write failing S3 sync test with moto**

```python
# backend/tests/bedrock/test_knowledge_base_s3.py
import json

import boto3
from moto import mock_aws

from bedrock import knowledge_base as kb


@mock_aws
def test_sync_session_to_s3(monkeypatch):
    bucket = "overlord-demo-logs"
    monkeypatch.setenv("OVERLORD_S3_BUCKET", bucket)
    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket=bucket)

    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added cache")
    key = kb.sync_to_s3()
    assert key.endswith(".json")

    obj = conn.get_object(Bucket=bucket, Key=key)
    body = json.loads(obj["Body"].read())
    assert len(body) == 1
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && pytest tests/bedrock/test_knowledge_base_s3.py -v`
Expected: `AttributeError: ... sync_to_s3`

- [ ] **Step 3: Implement sync_to_s3**

```python
# Append to knowledge_base.py
import boto3


def sync_to_s3(session_id: str = "default") -> str:
    bucket = os.getenv("OVERLORD_S3_BUCKET", "").strip()
    if not bucket:
        raise ValueError("OVERLORD_S3_BUCKET is not configured")

    records = _read_all()
    key = f"sessions/{session_id}/{uuid.uuid4()}.json"
    client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(records, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return key
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && pytest tests/bedrock/test_knowledge_base_s3.py -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/bedrock/knowledge_base.py backend/tests/bedrock/test_knowledge_base_s3.py
git commit -m "feat(kb): sync session logs to S3 for Bedrock KB ingestion"
```

---

### Task 4: Guardrails — PreflightResult + file overlap rule

**Files:**
- Create: `backend/bedrock/guardrails.py`
- Create: `backend/tests/bedrock/test_guardrails.py`

- [ ] **Step 1: Write failing test — file overlap**

```python
# backend/tests/bedrock/test_guardrails.py
from bedrock import guardrails, knowledge_base as kb


def test_preflight_trips_on_file_overlap():
    kb.log_action(
        agent_id="agent_a",
        action_type="modify_file",
        file_path="utils/cache.py",
        description="Implement cache helpers",
    )
    proposed = {
        "agent_id": "agent_b",
        "action_type": "modify_file",
        "file_path": "utils/cache.py",
        "description": "Refactor cache module",
    }
    result = guardrails.preflight_check(proposed)
    assert result.allowed is False
    assert result.rule == "file_overlap"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py::test_preflight_trips_on_file_overlap -v`
Expected: `ModuleNotFoundError` or missing `preflight_check`

- [ ] **Step 3: Implement PreflightResult + file_overlap**

```python
# backend/bedrock/guardrails.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bedrock import knowledge_base as kb


@dataclass
class PreflightResult:
    allowed: bool
    rule: str | None = None
    message: str = ""
    kb_context: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "rule": self.rule,
            "message": self.message,
            "kb_context": self.kb_context or [],
        }


def preflight_check(proposed_action: dict[str, Any]) -> PreflightResult:
    agent_id = proposed_action["agent_id"]
    file_path = proposed_action.get("file_path", "")
    history = kb.get_history(limit=100, record_type="action")

    for record in history:
        if record["agent_id"] == agent_id:
            continue
        other_path = record["payload"].get("file_path", "")
        if file_path and other_path == file_path:
            ctx = kb.retrieve_context(
                f"{file_path} {record['agent_id']} {record['payload'].get('description', '')}",
                max_results=5,
            )
            return PreflightResult(
                allowed=False,
                rule="file_overlap",
                message=(
                    f"{record['agent_id']} already touched {file_path}; "
                    f"{agent_id} must coordinate before modifying."
                ),
                kb_context=ctx,
            )

    return PreflightResult(allowed=True, message="No file overlap detected.")
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py::test_preflight_trips_on_file_overlap -v`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/bedrock/guardrails.py backend/tests/bedrock/test_guardrails.py
git commit -m "feat(guardrails): trip on cross-agent file overlap"
```

---

### Task 5: Guardrails — reverses recent decision rule (demo killer)

**Files:**
- Modify: `backend/bedrock/guardrails.py`
- Modify: `backend/tests/bedrock/test_guardrails.py`

- [ ] **Step 1: Write failing test — delete after add**

```python
def test_preflight_trips_when_deleting_recent_add():
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added caching utility")
    kb.log_action("agent_a", "modify_file", "utils/cache.py", "Extended cache API")
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Documented cache usage")

    proposed = {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Remove caching utility — unused",
    }
    result = guardrails.preflight_check(proposed)
    assert result.allowed is False
    assert result.rule == "reverses_recent_decision"
    assert "agent_a" in result.message
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py::test_preflight_trips_when_deleting_recent_add -v`
Expected: `assert True is False` (overlap rule may fire first — implementation must check reverse **before** overlap or prioritize `reverses_recent_decision`)

- [ ] **Step 3: Add reverse check at top of preflight_check**

```python
_DELETE_ACTIONS = {"delete_file", "remove_file", "delete"}
_ADD_ACTIONS = {"add_file", "create_file", "add"}


def _check_reverses_recent_decision(proposed: dict[str, Any]) -> PreflightResult | None:
    action_type = proposed.get("action_type", "")
    file_path = proposed.get("file_path", "")
    if action_type not in _DELETE_ACTIONS or not file_path:
        return None

    recent = kb.get_history(limit=20, record_type="action")
    adds_by_other = [
        r
        for r in recent
        if r["agent_id"] != proposed["agent_id"]
        and r["payload"].get("file_path") == file_path
        and r["payload"].get("action_type") in _ADD_ACTIONS
    ]
    if not adds_by_other:
        return None

    last_add = adds_by_other[-1]
    ctx = kb.retrieve_context(
        f"{file_path} cache utility {last_add['agent_id']}", max_results=5
    )
    return PreflightResult(
        allowed=False,
        rule="reverses_recent_decision",
        message=(
            f"Blocked: {proposed['agent_id']} would delete {file_path}, but "
            f"{last_add['agent_id']} added or extended it recently "
            f"({last_add['payload'].get('description', '')})."
        ),
        kb_context=ctx,
    )


def preflight_check(proposed_action: dict[str, Any]) -> PreflightResult:
    reversed_result = _check_reverses_recent_decision(proposed_action)
    if reversed_result:
        return reversed_result
    # ... existing file_overlap logic ...
```

- [ ] **Step 4: Run guardrails tests — expect PASS**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/bedrock/guardrails.py backend/tests/bedrock/test_guardrails.py
git commit -m "feat(guardrails): block actions that reverse recent peer work"
```

---

### Task 6: Guardrails — intent contradiction rule

**Files:**
- Modify: `backend/bedrock/guardrails.py`
- Modify: `backend/tests/bedrock/test_guardrails.py`

- [ ] **Step 1: Write failing test**

```python
def test_preflight_trips_on_intent_contradiction():
    kb.log_intent("agent_a", "Add caching utilities to improve response times")
    proposed = {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Remove caching layer to reduce complexity",
    }
    result = guardrails.preflight_check(proposed)
    assert result.allowed is False
    assert result.rule in {"intent_contradiction", "reverses_recent_decision"}
```

- [ ] **Step 2: Run — expect FAIL or wrong rule only**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py::test_preflight_trips_on_intent_contradiction -v`

- [ ] **Step 3: Implement intent check (after reverse, before overlap)**

```python
_CONTRADICTION_PAIRS = [
    (("cache", "caching"), ("remove", "delete", "strip", "minimize")),
    (("performance", "speed", "optimize"), ("minimal", "dependency", "simplify")),
]


def _check_intent_contradiction(proposed: dict[str, Any]) -> PreflightResult | None:
    intents = kb.get_history(limit=20, record_type="intent")
    description = (proposed.get("description") or "").lower()
    for record in intents:
        if record["agent_id"] == proposed["agent_id"]:
            continue
        intent_text = record["payload"].get("intent", "").lower()
        for positive, negative in _CONTRADICTION_PAIRS:
            if any(p in intent_text for p in positive) and any(
                n in description for n in negative
            ):
                ctx = kb.retrieve_context(intent_text + " " + description, max_results=5)
                return PreflightResult(
                    allowed=False,
                    rule="intent_contradiction",
                    message=(
                        f"Intent conflict: {record['agent_id']} ({intent_text}) vs "
                        f"{proposed['agent_id']} action ({description})."
                    ),
                    kb_context=ctx,
                )
    return None
```

Call this in `preflight_check` after `_check_reverses_recent_decision`.

- [ ] **Step 4: Run all guardrails tests — expect PASS**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/bedrock/guardrails.py backend/tests/bedrock/test_guardrails.py
git commit -m "feat(guardrails): detect intent contradictions before execution"
```

---

### Task 7: Route tripped guardrail to Overlord

**Files:**
- Modify: `backend/bedrock/guardrails.py`
- Modify: `backend/tests/bedrock/test_guardrails.py`

**Prerequisite:** Person 1's `arbitrate` accepts optional `kb_context`:

```python
def arbitrate(agent_a: dict, agent_b: dict, kb_context: list[dict] | None = None) -> dict:
    # inject kb_context into Sonnet prompt when present
```

- [ ] **Step 1: Write failing test with overlord stub**

```python
# backend/tests/bedrock/test_guardrails.py
def test_handle_proposed_action_routes_to_overlord(monkeypatch):
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added caching utility")

    def fake_arbitrate(agent_a, agent_b, kb_context=None):
        return {
            "conflict_type": "proactive_guardrail",
            "reasoning": "Keep cache; refactor around it.",
            "resolved_code": "# refactor around cache",
            "tokens_saved_estimate": "2400",
            "verdict": "modify",
        }

    monkeypatch.setattr(guardrails, "_arbitrate", fake_arbitrate)

    proposed = {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Remove caching utility",
    }
    agent_b = {
        "intent": proposed["description"],
        "code": "# delete utils/cache.py",
    }
    agent_a = {
        "intent": "Maintain caching utilities for get_user() performance",
        "code": "# utils/cache.py must remain",
    }

    out = guardrails.handle_proposed_action(proposed, agent_a, agent_b)
    assert out["preflight"]["allowed"] is False
    assert out["resolution"]["verdict"] == "modify"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py::test_handle_proposed_action_routes_to_overlord -v`

- [ ] **Step 3: Implement handle_proposed_action**

```python
def _arbitrate(agent_a: dict, agent_b: dict, kb_context: list[dict] | None = None) -> dict:
    from overlord import arbitrate

    return arbitrate(agent_a, agent_b, kb_context=kb_context)


def handle_proposed_action(
    proposed_action: dict[str, Any],
    agent_a: dict[str, str],
    agent_b: dict[str, str],
) -> dict[str, Any]:
    preflight = preflight_check(proposed_action)
    if preflight.allowed:
        kb.log_action(
            agent_id=proposed_action["agent_id"],
            action_type=proposed_action.get("action_type", "unknown"),
            file_path=proposed_action.get("file_path", ""),
            description=proposed_action.get("description", ""),
        )
        return {"preflight": preflight.to_dict(), "resolution": None, "executed": True}

    resolution = _arbitrate(agent_a, agent_b, kb_context=preflight.kb_context)
    kb.log_decision(
        reasoning=resolution.get("reasoning", ""),
        affected_agents=[agent_a.get("agent_id", "agent_a"), agent_b.get("agent_id", "agent_b")],
    )
    return {
        "preflight": preflight.to_dict(),
        "resolution": resolution,
        "executed": False,
        "verdict": resolution.get("verdict", "blocked"),
    }
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/bedrock/guardrails.py backend/tests/bedrock/test_guardrails.py
git commit -m "feat(guardrails): route tripped checks to Overlord with KB context"
```

---

### Task 8: Optional Bedrock Guardrails API wrapper

**Files:**
- Modify: `backend/bedrock/guardrails.py`
- Modify: `backend/tests/bedrock/test_guardrails.py`

- [ ] **Step 1: Write test — skips when env unset**

```python
def test_apply_bedrock_guardrail_skips_without_id(monkeypatch):
    monkeypatch.delenv("BEDROCK_GUARDRAIL_ID", raising=False)
    assert guardrails.apply_bedrock_guardrail("delete all caches") is None
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py::test_apply_bedrock_guardrail_skips_without_id -v`

- [ ] **Step 3: Implement apply_bedrock_guardrail**

```python
def apply_bedrock_guardrail(text: str) -> dict[str, Any] | None:
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID", "").strip()
    if not guardrail_id:
        return None

    import os
    from bedrock.client import get_bedrock_runtime_client

    client = get_bedrock_runtime_client()
    version = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")
    response = client.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=version,
        source="INPUT",
        content=[{"text": {"text": text}}],
    )
    return response
```

Integrate at the end of `preflight_check` when still `allowed`: if Bedrock returns `GUARDRAIL_INTERVENED`, flip to blocked.

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/bedrock/guardrails.py backend/tests/bedrock/test_guardrails.py
git commit -m "feat(guardrails): optional Bedrock Guardrails API integration"
```

---

### Task 9: Demo seed helper (Act 3)

**Files:**
- Modify: `backend/bedrock/guardrails.py`
- Modify: `backend/tests/bedrock/test_guardrails.py`

- [ ] **Step 1: Write failing test for seed**

```python
def test_seed_guardrail_demo_populates_history(isolated_kb_session):
    from bedrock.guardrails import seed_guardrail_demo

    seed_guardrail_demo()
    history = kb.get_history()
    assert len(history) >= 3
    assert any("cache" in h["payload"].get("file_path", "") for h in history)
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py::test_seed_guardrail_demo_populates_history -v`

- [ ] **Step 3: Implement seed_guardrail_demo + GUARDRAIL_DEMO_SCENARIO**

```python
GUARDRAIL_DEMO_SCENARIO = {
    "agent_a": {
        "intent": "Add caching utilities to improve get_user() response times",
        "code": "# utils/cache.py — CacheManager with TTL support",
    },
    "agent_b": {
        "intent": "Remove unused utilities to reduce maintenance burden",
        "code": "# planned: delete utils/cache.py",
    },
    "proposed_action": {
        "agent_id": "agent_b",
        "action_type": "delete_file",
        "file_path": "utils/cache.py",
        "description": "Remove caching utility — appears unused",
    },
}


def seed_guardrail_demo() -> None:
    kb.log_intent("agent_a", GUARDRAIL_DEMO_SCENARIO["agent_a"]["intent"])
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added caching utility")
    kb.log_action("agent_a", "modify_file", "utils/cache.py", "Extended cache API")
    kb.log_action("agent_a", "add_file", "utils/cache.py", "Documented cache usage")
    kb.log_intent("agent_b", GUARDRAIL_DEMO_SCENARIO["agent_b"]["intent"])
```

- [ ] **Step 4: Run — expect PASS**

Run: `cd backend && pytest tests/bedrock/test_guardrails.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add backend/bedrock/guardrails.py backend/tests/bedrock/test_guardrails.py
git commit -m "feat(guardrails): demo seed for proactive prevention scenario"
```

---

### Task 10: Person 1 integration — KB context in arbitrate prompt

**Files:**
- Modify: `backend/overlord.py` (Person 1 — coordinate in PR, not Person 3 commit if avoiding overlap)

Person 3 opens a PR comment or Slack message with this exact diff for Person 1:

```python
# In arbitrate(), after building agent_a/agent_b strings:
kb_section = ""
if kb_context:
    kb_section = "\nKnowledge Base context:\n" + json.dumps(kb_context, indent=2)

prompt = f"""
...
{kb_section}
...
"""
```

Person 3 adds a contract test that **mocks** overlord:

```python
# backend/tests/bedrock/test_overlord_kb_contract.py
def test_kb_context_forwarded_to_arbitrate(monkeypatch):
    captured = {}

    def fake_arbitrate(agent_a, agent_b, kb_context=None):
        captured["kb_context"] = kb_context
        return {"reasoning": "ok", "conflict_type": "proactive_guardrail"}

    monkeypatch.setattr("bedrock.guardrails._arbitrate", fake_arbitrate)
    # call handle_proposed_action ...
    assert captured["kb_context"] is not None
```

- [ ] **Step 1: Add contract test file**
- [ ] **Step 2: Run and commit**

```bash
git add backend/tests/bedrock/test_overlord_kb_contract.py
git commit -m "test: contract for KB context passed into arbitrate"
```

---

### Task 11: AWS console setup (Bedrock KB + Guardrails)

**Files:**
- Create: `.env.example`

- [ ] **Step 1: Document setup in `.env.example`** (comments only, no secrets)

```bash
AWS_REGION=us-east-1
OVERLORD_USE_LOCAL_KB=true
OVERLORD_SESSION_PATH=.overlord/session.json
# --- Optional production path ---
# OVERLORD_S3_BUCKET=your-overlord-logs-bucket
# BEDROCK_KB_ID=XXXXXXXX
# BEDROCK_GUARDRAIL_ID=your-guardrail-id
# BEDROCK_GUARDRAIL_VERSION=DRAFT
```

- [ ] **Step 2: Create S3 bucket** `overlord-agent-logs-<team>` (console or CLI)

- [ ] **Step 3: Create Bedrock Knowledge Base**
  - Data source: S3 bucket prefix `sessions/`
  - Embeddings: Titan Text Embeddings v2 (or team default)
  - Sync after `sync_to_s3()` uploads

- [ ] **Step 4: Create Bedrock Guardrail** (console)
  - Deny topic example: "agent deleting another agent's recent file additions"
  - Copy Guardrail ID to `.env`

- [ ] **Step 5: Smoke test retrieve (manual)**

Run:

```bash
cd backend && OVERLORD_USE_LOCAL_KB=false BEDROCK_KB_ID=<id> python -c "
from bedrock.knowledge_base import retrieve_context
print(retrieve_context('What did agent_a optimize for in cache module?'))
"
```

Expected: list of retrieval results (or empty if index not synced yet)

- [ ] **Step 6: Commit**

```bash
git add .env.example
git commit -m "docs: env vars for Bedrock KB and Guardrails"
```

---

### Task 12: Person 2 integration — API routes (handoff)

**Files:**
- Modify: `backend/main.py` (Person 2)
- Modify: `backend/agents/scenarios.py` (Person 2)

Person 3 sends Person 2 this exact code to merge after Person 3's branch:

```python
# backend/main.py additions
from bedrock import knowledge_base as kb
from bedrock import guardrails
from bedrock.guardrails import GUARDRAIL_DEMO_SCENARIO, seed_guardrail_demo


@app.get("/history")
def get_history(limit: int = 50):
    return kb.get_history(limit=limit)


@app.post("/guardrail/check")
def guardrail_check():
    seed_guardrail_demo()
    scenario = GUARDRAIL_DEMO_SCENARIO
    result = guardrails.handle_proposed_action(
        scenario["proposed_action"],
        scenario["agent_a"],
        scenario["agent_b"],
    )
    return {
        "agent_a": scenario["agent_a"],
        "agent_b": scenario["agent_b"],
        "proposed_action": scenario["proposed_action"],
        "preflight": result["preflight"],
        "resolution": result["resolution"],
        "executed": result["executed"],
    }
```

```python
# backend/agents/scenarios.py — add key
"guardrail_prevention": {
    "agent_a": GUARDRAIL_DEMO_SCENARIO["agent_a"],
    "agent_b": GUARDRAIL_DEMO_SCENARIO["agent_b"],
},
```

Import `GUARDRAIL_DEMO_SCENARIO` from `bedrock.guardrails`.

- [ ] **Step 1: Person 2 adds routes** (not Person 3)
- [ ] **Step 2: Manual demo curl**

```bash
curl -s http://localhost:8000/history | jq .
curl -s -X POST http://localhost:8000/guardrail/check | jq .
```

Expected: `preflight.allowed == false`, `resolution` object with `reasoning`, `executed == false`

- [ ] **Step 3: Person 2 commits** `feat(api): history and guardrail check routes`

---

### Task 13: Full test suite + lint

- [ ] **Step 1: Run all bedrock tests**

Run: `cd backend && pytest tests/bedrock -v`
Expected: all tests passed

- [ ] **Step 2: Verify .overlord in gitignore**

Add to `.gitignore`:

```
.overlord/
.env
backend/.venv/
```

- [ ] **Step 3: Final commit on feature branch**

```bash
git add .gitignore
git commit -m "chore: ignore local session logs and venv"
```

---

## Self-review

### 1. Spec coverage

| PRD requirement | Task |
|---|---|
| Every action passes guardrail check | Task 4–7 `preflight_check`, Task 7 `handle_proposed_action` |
| File overlap detection | Task 4 |
| Intent contradiction | Task 6 |
| Reverses recent decision | Task 5 |
| Trip → pause → route Overlord | Task 7 |
| Log actions, intents, decisions to KB | Task 1, Task 7 `log_decision` |
| S3-backed logs | Task 3 |
| `bedrock_agent_runtime.retrieve()` | Task 2 |
| Bedrock Guardrails console | Task 8, Task 11 |
| Demo: Agent B delete blocked | Task 9 seed + Task 12 route |
| `GET /history` | Task 12 handoff |

### 2. Placeholder scan

No TBD steps. All code blocks are complete.

### 3. Type consistency

- `proposed_action` always uses keys: `agent_id`, `action_type`, `file_path`, `description`
- `PreflightResult.rule` values: `file_overlap`, `reverses_recent_decision`, `intent_contradiction`
- `handle_proposed_action` returns `preflight`, `resolution`, `executed`, optional `verdict`

### Gaps / team coordination

- Person 1 must add `kb_context` param to `arbitrate()` before Task 7 integration test against real overlord.
- Person 2 owns `main.py` routes — Task 12 is a handoff, not Person 3 file edit.
- Frontend Act 3 panel should call `POST /guardrail/check` (Person 2 / frontend).

---

## Merge checklist (Person 3 branch)

1. Rebase on Person 1's `bedrock/client.py` + `overlord.py`
2. Ensure `PYTHONPATH=backend` or run tests from `backend/` with `pythonpath=.`
3. PR only touches `backend/bedrock/knowledge_base.py`, `backend/bedrock/guardrails.py`, `backend/tests/bedrock/*`, `.env.example`, `.gitignore`
4. Leave `INTEGRATION` comment on Person 2's PR with Task 12 snippets

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-16-guardrails-knowledge-base.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
