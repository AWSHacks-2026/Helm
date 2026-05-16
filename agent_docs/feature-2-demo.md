# Feature 2 Demo: Intent Conflict Resolution

## Scenario

This demo uses the Performance vs Minimalism scenario to show Overlord resolving an intent conflict before either agent writes contradictory code.

Agent A intent:

> I am optimizing this module for maximum performance, even if it means adding specialized caching and parsing dependencies.

Agent B intent:

> I am refactoring this module to minimize external dependencies and keep the deployment artifact small.

These intents conflict before code is written because Agent A wants to add performance dependencies while Agent B wants to remove or minimize dependencies. Without Overlord, one agent could add specialized parsing or caching libraries while the other removes those same dependencies to keep the deployment artifact small.

## Run The API

From the worktree root, activate the user's environment:

```bash
source "$HOME/.bashrc" && activatevenv
```

Then start the FastAPI app with the backend directory on `PYTHONPATH`:

```bash
PYTHONPATH=overlord/backend uvicorn main:app --reload
```

Expected startup line:

```text
Uvicorn running on http://127.0.0.1:8000
```

Alternatively, from `overlord/backend`, run:

```bash
uvicorn main:app --reload
```

## Demo Calls

List scenarios:

```bash
curl http://127.0.0.1:8000/scenarios
```

Expected response includes at least the Feature 1, Feature 2, dependency, and Feature 3 demo scenarios:

```json
[
  "merge_conflict",
  "intent_conflict",
  "dependency_conflict",
  "guardrail_prevention"
]
```

Resolve the intent conflict:

```bash
curl -X POST http://127.0.0.1:8000/resolve/intent_conflict
```

Expected resolution fields include:

```json
{
  "resolution": {
    "conflict_type": "intent_conflict",
    "compatibility": "conflict",
    "unified_intent": "Optimize for performance where measurable, but prefer native Python implementations unless a dependency saves at least 20% latency on the demo path.",
    "priority_order": [
      "preserve deployability and low dependency count",
      "improve latency with standard-library techniques first",
      "allow a new dependency only with benchmark evidence"
    ],
    "agent_updates": {
      "agent_a": "Benchmark stdlib json plus functools.lru_cache before proposing orjson.",
      "agent_b": "Keep dependency removals unless Agent A provides benchmark evidence for a targeted exception."
    },
    "tokens_saved_estimate": "2400 tokens saved (75%)"
  }
}
```

The response may include additional context fields such as `agent_a`, `agent_b`, `reasoning`, `resolved_code`, and `history_used`.

## Judge Narrative

Overlord catches the conflict before either agent writes contradictory code. It aligns them on native Python first, benchmarks the demo path, and allows a dependency only if it saves at least 20% latency.
