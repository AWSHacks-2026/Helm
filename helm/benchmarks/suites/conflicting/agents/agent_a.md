# Agent: agent_a

**agent_id:** `agent_a`

## Scope

- `app/streams/live.py` only

## Task

Add RTMP ingest hooks and stream lifecycle extensions to `app/streams/live.py`.

## Helm MCP

Declare intent before editing; use guardrail hook on writes.

## Git

Commit: `feat(agent_a): <summary>`. Do not resolve merge conflicts—report `merge_conflict` via `helm_record_checkpoint`.
