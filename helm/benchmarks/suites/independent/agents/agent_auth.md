# Agent: agent_auth

**agent_id:** `agent_auth`

## Scope

You may edit only:

- `app/auth/handlers.py`
- `app/auth/models.py`

## Task

Implement JWT register/login in `app/auth/handlers.py` per the suite manifest feature description.

## Helm MCP (required when `HELM_ENABLED=1`)

1. Call `helm_declare_intent` before your first edit (session from `HELM_TEAM_SESSION`, agent_id `agent_auth`).
2. All writes go through the PreToolUse hook (`helm_guardrail_check`).

## Git

- Commit when done: `feat(agent_auth): <short summary>`
- Do **not** run `git merge` or resolve conflicts manually—stop and report.

## Checkpoint

Call `helm_record_checkpoint` with events: `started`, `committed`.
