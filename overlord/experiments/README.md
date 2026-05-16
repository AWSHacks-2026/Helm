# Multi-agent conflict experiments

Four unrelated mini-projects. Two or more Haiku agents implement the same feature on the same files **without Overlord**. Metrics are written to `results/`.

## Themes

| Theme | Focus | Conflicting file |
|-------|--------|------------------|
| `stellar_cartography` | Star chart API | `app/services/constellation_lookup.py` |
| `aquarium_logistics` | Tank feeding schedule | `app/scheduling/feeding_planner.py` |
| `vinyl_catalog` | Record catalog | `app/catalog/tracks.py` |
| `trail_rations` | Meal calories | `app/planning/meal_estimator.py` |

## Metrics

| Metric | Meaning |
|--------|---------|
| **Conflict edits** | Files where two agents produced different code for the same path |
| **Reverted commits** | Files where sequential apply (alpha → beta) lost most of alpha’s content |
| **Total tokens** | Sum of Haiku input + output tokens |
| **Resolution time** | Wall-clock ms for all agent calls |
| **Agent success rate** | Share of agent runs with valid Python output |
| **Merge success rate** | Share of files that still parse after both agents’ changes are applied in order |

## Run (mock — no AWS cost)

```bash
cd overlord
source .venv/bin/activate
export OVERLORD_MOCK_BEDROCK=1
python scripts/run_agent_experiment.py --mock
```

## Run (live Bedrock)

```bash
export OVERLORD_MOCK_BEDROCK=0
export OVERLORD_AGENT_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
python scripts/run_agent_experiment.py
```

Optional: one theme only

```bash
python scripts/run_agent_experiment.py --mock --themes stellar_cartography
```

Output: `experiments/results/report_<timestamp>.md` and `.json`

## Tests

```bash
cd overlord/backend
OVERLORD_MOCK_BEDROCK=1 python -m pytest tests/test_experiment_metrics.py -v
```
