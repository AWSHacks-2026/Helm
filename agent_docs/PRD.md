# HELM
## Multi-Agent Conflict Resolution System
**Product Requirements Document | AWS Bedrock Hackathon**

| | |
|---|---|
| Hackathon Track | AWS Bedrock |
| Team Size | 3 Engineers |
| Version | 1.0 — Hackathon Build |
| Date | May 2026 |

---

## 1. Executive Summary

Helm is a supervisor agent system built on AWS Bedrock that sits above multiple AI coding agents and resolves conflicts before they waste tokens, time, and developer sanity.

The core problem: in multi-agent coding environments, agents working in parallel inevitably conflict — either at the code level (merge conflicts) or at the intent level (contradictory goals). Today, each agent independently attempts to fix these conflicts, burning tokens and producing thrash. Helm intercepts these conflicts, arbitrates a unified resolution, and eliminates the back-and-forth entirely.

> **Core Thesis:** A single orchestrator agent that understands all agents' code state and intent resolves conflicts in one pass, dramatically reducing token usage compared to agents resolving conflicts independently.

---

## 2. Problem Statement

### 2.1 The Multi-Agent Conflict Problem

As AI coding agents become more capable, teams are deploying multiple agents to work on the same codebase simultaneously. This introduces three categories of expensive conflicts:

| Conflict Type | What Happens | Current Cost |
|---|---|---|
| Merge Conflict | Two agents modify the same file or function differently, producing incompatible diffs | Both agents attempt to fix it independently, doubling token spend |
| Intent Conflict | Agent A optimizes for speed, Agent B optimizes for readability — their outputs directly contradict each other | Agents loop trying to satisfy conflicting goals indefinitely |
| Dependency Conflict | Agent A adds a library, Agent B removes it or pins a different version | Build breaks, agents diagnose independently without shared context |

### 2.2 Why Existing Approaches Fail

- No shared context: agents don't know what other agents are doing or why
- Reactive only: conflicts are discovered after they cause damage
- Token waste compounds: each agent burns tokens re-analyzing the same conflict
- No arbitration authority: there's no single agent with a mandate to decide the right answer

---

## 3. Solution Overview

### 3.1 Architecture

Helm is a three-layer system:

```
[Agent A Simulator] ──┐
                       ├──► [Helm Agent (Bedrock)] ──► [Resolved Output]
[Agent B Simulator] ──┘
         ▲
   [Guardrails Layer — intercepts before execution]
```

| Layer | Responsibility |
|---|---|
| 1. Sub-Agent Simulators | Produce pre-scripted conflict scenarios representing realistic agent outputs. In demo: simulated. Post-hackathon: real agents. |
| 2. Helm Agent | Core arbitration logic. Takes both agents' code + intent, calls Claude Sonnet via Bedrock, returns a unified resolution with reasoning. |
| 3. Guardrails Layer | Proactive pre-flight check before agent actions execute. Catches conflicts before they happen and routes to Helm early. |

### 3.2 AWS Bedrock Integration

- **Claude Sonnet 4 via Bedrock** — Helm arbitration. Used only for conflict resolution — the expensive reasoning step.
- **Claude Haiku 3 via Bedrock** — Sub-agent simulation. Cheaper, faster model handles routine agent tasks.
- **Bedrock Knowledge Base** — Shared agent memory. Stores each agent's action history, declared intents, and past decisions so the Helm has full context.
- **Bedrock Guardrails** — Proactive conflict prevention. Intercepts agent actions before execution and flags potential conflicts.
- **Bedrock Multi-Agent Supervisor** — Native orchestration framework. Helm is implemented as a Bedrock supervisor agent with sub-agents wired to it.

> **Token Efficiency Strategy:** Model tiering is central to the token efficiency story. By using Haiku for routine tasks and only escalating to Sonnet for actual conflict resolution, Helm minimizes cost while maximizing resolution quality.

---

## 4. Features

### Feature 1: Merge Conflict Resolution
**Owner: Person 1**

Detects and resolves conflicts where two agents have produced incompatible diffs to the same code.

#### How it works
- Agent A and Agent B each produce a modified version of a function or file
- Helm receives both versions along with each agent's stated intent
- Claude Sonnet analyzes the structural diff and produces a single unified resolution
- Resolution includes the merged code, reasoning, and which agent's approach was prioritized and why

#### Bedrock specifics
- Raw `invoke_model` call to Claude Sonnet with structured conflict payload
- Response parsed as JSON with fields: `conflict_type`, `reasoning`, `resolved_code`, `tokens_saved_estimate`
- Agent histories retrieved from Knowledge Base to inform the resolution

#### Demo scenario
> **Scenario: Cache vs. Readability**
> Agent A adds a caching layer to `get_user()`. Agent B refactors `get_user()` for readability, removing the cache and adding type hints. Helm produces a version that caches AND has type hints — respecting both intents.

---

### Feature 2: Intent Conflict Resolution
**Owner: Person 2**

Detects and resolves conflicts where two agents have contradictory goals that would produce incompatible outputs even if their code doesn't directly overlap.

#### How it works
- Each agent declares its intent at task start: what it is optimizing for and why
- Intent declarations are stored in the Knowledge Base
- Before executing, the Helm checks if declared intents are compatible
- If they conflict, Helm arbitrates a priority order or a compromise intent before either agent acts
- Agents then execute with aligned goals, preventing the conflict from ever manifesting in code

#### Bedrock specifics
- Knowledge Base retrieval to pull both agents' historical intents and decisions
- Prompt engineering focuses on goal compatibility analysis, not just code diff analysis
- Returns a unified intent statement both agents are updated with before continuing

#### Demo scenario
> **Scenario: Performance vs. Minimalism**
> Agent A declares: "I am optimizing this module for maximum performance." Agent B declares: "I am refactoring this module to minimize dependencies." These produce opposite results on the same codebase. Helm arbitrates: "Optimize for performance where it doesn't add dependencies; prefer native implementations."

---

### Feature 3: Guardrails + Knowledge Base
**Owner: Person 3**

Proactive conflict prevention layer that intercepts agent actions before execution and routes to the Helm early, before tokens are wasted on conflicting work.

#### Guardrails — how it works
- Every agent action passes through a Guardrail check before executing
- Guardrail checks: does this action touch a file another agent is working on? Does this contradict a logged intent? Does this reverse a recent decision?
- If a guardrail trips, the action is paused and routed to Helm
- Helm arbitrates proactively and returns a go/no-go with optional modifications

#### Knowledge Base — how it works
- Every agent action, intent declaration, and Helm decision is written to the KB
- KB is an S3-backed Bedrock Knowledge Base with semantic search
- Helm queries KB before every arbitration: "What has Agent A been optimizing for? What decisions have been made in this module?"
- This gives the Helm long-term memory across the entire session

#### Bedrock specifics
- `bedrock_agent_runtime.retrieve()` for KB queries
- Guardrails configured via Bedrock console with custom deny topics and content filters
- S3 bucket stores agent logs as structured JSON; KB indexes them for semantic retrieval

#### Demo scenario
> **Scenario: Proactive Prevention**
> Agent B is about to delete a caching utility. Guardrail detects Agent A added this utility 3 actions ago and flags it. Helm intervenes before Agent B executes, reviews both agents' history in the KB, and instructs Agent B to refactor around the utility instead of deleting it. Zero tokens wasted on conflicting execution.

---

## 5. Technical Specification

### 5.1 Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend | Python 3.11 + FastAPI | Async routes, easy boto3 integration |
| AWS SDK | boto3 | bedrock-runtime + bedrock-agent-runtime clients |
| AI Models | Claude Sonnet 4 / Haiku 3 | Via Bedrock invoke_model and Agents API |
| Memory | Bedrock Knowledge Base + S3 | Agent history, intents, decisions |
| Guardrails | Bedrock Guardrails | Pre-flight conflict checks |
| Frontend | React + Vite (Cursor-generated) | Three-panel UI, token counter |
| Config | python-dotenv | AWS creds kept out of code |

### 5.2 Project Structure

```
helm/
├── backend/
│   ├── main.py                    # FastAPI app — all routes, token counter
│   ├── helm.py                # Core arbitrate() function
│   ├── agents/
│   │   ├── simulator.py           # Packages scenarios into agent output format
│   │   └── scenarios.py           # 3 pre-scripted conflict scenarios
│   └── bedrock/
│       ├── client.py              # boto3 client setup
│       ├── knowledge_base.py      # KB read/write helpers
│       └── guardrails.py          # Pre-flight check logic
├── frontend/                      # Generated by Cursor from API contract
└── .env                           # AWS keys — gitignore this
```

### 5.3 API Contract

**All three people must agree on this before splitting work.**

`POST /resolve/{scenario_name}` returns:

```json
{
  "agent_a": {
    "intent": "string — what Agent A declared it was trying to do",
    "code": "string — Agent A's code output"
  },
  "agent_b": {
    "intent": "string — what Agent B declared it was trying to do",
    "code": "string — Agent B's code output"
  },
  "resolution": {
    "conflict_type": "merge_conflict | intent_conflict | dependency_conflict",
    "reasoning": "string — Helm's explanation of the resolution decision",
    "resolved_code": "string — the unified output code",
    "tokens_saved_estimate": "string — estimated tokens saved vs no-helm scenario"
  }
}
```

Other routes:
- `GET /scenarios` — returns list of available scenario names
- `GET /history` — returns agent action log from Knowledge Base

### 5.4 Bedrock Model IDs

```
Helm (Sonnet 4):   us.anthropic.claude-sonnet-4-20250514-v1:0
Sub-agents (Haiku 3):  us.anthropic.claude-haiku-3-20240307-v1:0
Region:                us-east-1
```

### 5.5 Core Code Scaffolding

**`backend/bedrock/client.py`**
```python
import boto3
from dotenv import load_dotenv

load_dotenv()

def get_bedrock_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1"
    )

def get_bedrock_agent_client():
    return boto3.client(
        service_name="bedrock-agent-runtime",
        region_name="us-east-1"
    )
```

**`backend/helm.py`**
```python
import json
from bedrock.client import get_bedrock_client

HELM_MODEL = "us.anthropic.claude-sonnet-4-20250514-v1:0"

def arbitrate(agent_a: dict, agent_b: dict) -> dict:
    client = get_bedrock_client()

    prompt = f"""
    You are a conflict resolution helm managing two AI coding agents.

    Agent A Intent: {agent_a['intent']}
    Agent A Code:
    {agent_a['code']}

    Agent B Intent: {agent_b['intent']}
    Agent B Code:
    {agent_b['code']}

    Your job:
    1. Identify the exact nature of the conflict
    2. Determine the best unified solution that respects both intents where possible
    3. Produce the resolved code
    4. Explain your reasoning

    Respond ONLY in JSON with no preamble:
    {{
        "conflict_type": "...",
        "reasoning": "...",
        "resolution": "...",
        "resolved_code": "...",
        "tokens_saved_estimate": "..."
    }}
    """

    response = client.invoke_model(
        modelId=HELM_MODEL,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        })
    )

    result = json.loads(response['body'].read())
    return json.loads(result['content'][0]['text'])
```

**`backend/agents/scenarios.py`**
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
            """
        },
        "agent_b": {
            "intent": "I am refactoring this function for readability and adding type hints",
            "code": """
def get_user(user_id: str) -> User:
    return db.query(user_id)
            """
        }
    },
    "intent_conflict": {
        "agent_a": {
            "intent": "I am optimizing this module for maximum performance",
            "code": "# Agent A's performance-optimized implementation here"
        },
        "agent_b": {
            "intent": "I am refactoring this module to minimize external dependencies",
            "code": "# Agent B's minimal-dependency implementation here"
        }
    },
    "dependency_conflict": {
        "agent_a": {
            "intent": "I am adding Redis for caching to improve response times",
            "code": "# requirements.txt addition: redis==4.6.0"
        },
        "agent_b": {
            "intent": "I am removing unnecessary dependencies to reduce image size",
            "code": "# requirements.txt: removed redis, replaced with in-memory dict"
        }
    }
}
```

**`backend/main.py`**
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agents.scenarios import SCENARIOS
from helm import arbitrate

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.get("/scenarios")
def get_scenarios():
    return list(SCENARIOS.keys())

@app.post("/resolve/{scenario_name}")
def resolve_conflict(scenario_name: str):
    if scenario_name not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")
    scenario = SCENARIOS[scenario_name]
    resolution = arbitrate(scenario["agent_a"], scenario["agent_b"])
    return {
        "agent_a": scenario["agent_a"],
        "agent_b": scenario["agent_b"],
        "resolution": resolution
    }
```

---

## 6. Work Split

Three equal vertical slices. Each person owns a full feature end to end. No file overlap.

| Person | Feature | Files Owned |
|---|---|---|
| Person 1 | Merge Conflict Resolution | `bedrock/client.py`, `helm.py` — AWS setup, `arbitrate()`, model tiering, prompt engineering |
| Person 2 | Intent Conflict Resolution | `agents/scenarios.py`, `agents/simulator.py`, `main.py` — 3 conflict scenarios, FastAPI routes, token counter, response shaping |
| Person 3 | Guardrails + Knowledge Base | `bedrock/knowledge_base.py`, `bedrock/guardrails.py` — KB read/write, Guardrail pre-flight checks, proactive routing |

> **Merge order:** Person 1 first (no dependencies), Person 3 second (pure bedrock/ folder), Person 2 last (imports from both). Frontend generated by Cursor after API is stable.

---

## 7. Demo Plan

### 7.1 Three-Act Structure

| Act | Feature | What Judges See |
|---|---|---|
| 1 | Merge Conflict | Two agents produce conflicting code. Helm resolves in one pass with clear reasoning. Token counter shows savings. |
| 2 | Intent Conflict | Two agents have contradictory goals. Helm identifies the incompatibility and produces a unified directive before any code is written. |
| 3 | Guardrails | Agent is about to do something that would conflict. Guardrail catches it before execution. Helm proactively prevents the conflict. Zero wasted tokens. |

### 7.2 The Killer Metric

Every resolution screen shows:

- Tokens used **WITH Helm:** ~800
- Tokens used **WITHOUT Helm** (agents thrashing): ~3,200
- **Savings: ~75%**

> Use real token counts from actual Bedrock runs — not estimates. Run test scenarios before the demo and plug in the real numbers.

---

## 8. Build Timeline

| Phase | When | Goal |
|---|---|---|
| Phase 1 — Unblock | Tonight, first 1hr | AWS account created, Bedrock access enabled, boto3 installed, API contract agreed |
| Phase 2 — Core Loop | Tonight, next 3hr | `arbitrate()` calling Bedrock and returning JSON, FastAPI `/resolve` route working, one scenario end to end |
| Phase 3 — All 3 Features | Tomorrow morning | All 3 conflict types working, KB storing history, Guardrails intercepting |
| Phase 4 — Frontend | Tomorrow midday | Cursor generates UI from API contract, token counter visible |
| Phase 5 — Demo Polish | 1hr before judging | Run all 3 scenarios, lock in real token numbers, rehearse the narrative |

> **Critical Path Warning:** The single most important thing tonight is getting AWS + Bedrock access enabled and one end-to-end Bedrock API call working. Everything else can be built tomorrow. An account that hasn't been approved for model access the night before is the most common hackathon blocker.

---

## 9. AWS Setup Checklist

Complete in this order before splitting work:

1. Create AWS account at aws.amazon.com (use personal email)
2. Navigate to Bedrock → Model Access → Request Access for **Claude Sonnet 4** and **Claude Haiku 3**
3. IAM → Create User → Attach `AmazonBedrockFullAccess` + `AmazonS3FullAccess` policies
4. Generate Access Key + Secret from IAM user — save securely
5. Run: `pip install boto3 python-dotenv fastapi uvicorn`
6. Run: `aws configure` — paste keys, set region to `us-east-1`
7. Verify: run a test `invoke_model` call to Claude Haiku before splitting work

---

## 10. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Bedrock model access not approved in time | HIGH | Request access tonight immediately. Have Claude.ai as backup to demo the prompts if API access fails. |
| Knowledge Base infra takes too long to set up | MEDIUM | Build KB integration last. Core demo works without it — KB is an enhancement, not critical path. |
| Helm resolution quality is poor | MEDIUM | Prompt engineering is the lever. Allocate time to iterate on the arbitration prompt with real test cases. |
| Three-person merge causes conflicts (ironic) | LOW | Strict folder ownership + agreed API contract eliminates overlap. Merge in order: P1, P3, P2. |
| Demo scenario feels fake to judges | LOW | Use real-looking code in scenarios. Frame as simulation explicitly — judges understand hackathon constraints. |

---

*Helm | AWS Bedrock Hackathon | Confidential*