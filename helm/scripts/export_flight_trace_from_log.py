#!/usr/bin/env python3
"""Build a FlightTrace JSON from live_matrix_run.log tqdm phase lines."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
TASKS = REPO / "shopfix" / "scenarios" / "tasks.yaml"

PHASE_RE = re.compile(
    r"phase=(?P<phase>[^,\]]+)(?:,|\])",
)
BLOCK_RE = re.compile(
    r"(?P<path>shopfix|streamcast)\s+(?P<path_mode>baseline|helm)\s+"
    r"(?P<suite>contention|disjoint)\s+n(?P<n>\d+)",
)


def load_task_map() -> dict[str, dict[str, str]]:
    try:
        import yaml
    except ImportError:
        return {}

    if not TASKS.is_file():
        return {}
    raw = yaml.safe_load(TASKS.read_text(encoding="utf-8")) or {}
    out: dict[str, dict[str, str]] = {}
    for task in raw.get("tasks") or []:
        tid = task.get("task_id")
        if not tid:
            continue
        files = task.get("files") or {}
        out[tid] = {
            "intent": str(task.get("intent", "")),
            "file": str(files.get("primary", "")),
        }
    return out


def parse_phase(phase: str, tasks: dict[str, dict[str, str]]) -> dict:
    """Parse agent_a:t01:edit style phases."""
    if phase == "dedup":
        return {"kind": "helm_dedup", "helm_action": "dedup", "file": ""}
    if phase.startswith("merge_fix:"):
        return {
            "kind": "helm_merge",
            "helm_action": "merge",
            "file": phase.split(":", 1)[1],
        }
    if ":" in phase:
        agent_part, rest = phase.split(":", 1)
        if ":" in rest:
            task_id, step = rest.split(":", 1)
        else:
            task_id, step = rest, "edit"
        meta = tasks.get(task_id, {})
        return {
            "kind": step,
            "agent_id": agent_part,
            "task_id": task_id,
            "intent": meta.get("intent", task_id),
            "file": meta.get("file", ""),
        }
    return {"kind": phase, "file": ""}


def agent_status_for_step(step_kind: str, *, blocked: bool) -> str:
    if blocked or step_kind == "guardrail":
        return "blocked"
    if step_kind in ("edit", "intent", "commit"):
        return "coding"
    if step_kind == "reassign":
        return "reassigned"
    if step_kind == "merge":
        return "conflicted"
    return "coding"


def build_frames(
    phases: list[dict],
    *,
    agent_ids: list[str],
    primary_file: str,
    path_mode: str,
    gate_skipped: bool | None,
    guardrails_blocked: int | None,
) -> list[dict]:
    agents_state = {
        aid: {
            "id": aid,
            "status": "idle",
            "taskTitle": "—",
            "filePath": primary_file,
        }
        for aid in agent_ids
    }
    frames: list[dict] = []
    at_ms = 0

    for index, step in enumerate(phases):
        helm = {"active": False}
        file_status = "clean"
        snippet_key = "auth_clean"
        primary = step.get("file") or primary_file

        kind = step.get("kind", "")
        if kind == "helm_dedup":
            helm = {"active": True, "action": "dedup", "detail": "Fleet dedup on overlapping work"}
            for aid in agent_ids:
                if agents_state[aid]["status"] != "reassigned":
                    agents_state[aid]["status"] = "blocked" if aid == agent_ids[-1] else "coding"
        elif kind == "helm_merge":
            if path_mode == "helm":
                helm = {"active": True, "action": "merge", "detail": f"Helm merge on {primary}"}
            else:
                helm = {"active": False}
            file_status = "merged" if index == len(phases) - 1 else "conflict"
            if "auth.py" in primary:
                snippet_key = (
                    "auth_agent_b_edit" if file_status == "conflict" else "auth_clean"
                )
            else:
                snippet_key = "cart_conflict" if file_status == "conflict" else "cart_merged"
            for aid in agent_ids:
                agents_state[aid]["status"] = (
                    "complete" if file_status == "merged" else "conflicted"
                )
        elif kind == "guardrail":
            aid = step.get("agent_id", agent_ids[0])
            helm = {"active": True, "action": "guardrail", "detail": "Blocked write before it lands"}
            agents_state[aid]["status"] = "blocked"
            file_status = "blocked"
            snippet_key = "auth_guardrail_blocked"
        elif kind == "edit" and step.get("agent_id"):
            aid = step["agent_id"]
            agents_state[aid]["status"] = "coding"
            agents_state[aid]["taskTitle"] = step.get("intent", aid)[:72]
            agents_state[aid]["filePath"] = primary
            file_status = "editing"
            snippet_key = "auth_agent_a_edit" if aid == agent_ids[0] else "auth_agent_b_edit"
        elif kind == "commit" and step.get("agent_id"):
            aid = step["agent_id"]
            agents_state[aid]["status"] = "complete"

        edges = _build_edges(list(agents_state.values()), helm)

        frames.append(
            {
                "id": f"live-{index}",
                "atMs": at_ms,
                "title": _title_for_step(step),
                "narration": _narration_for_step(
                    step, path_mode=path_mode, gate_skipped=gate_skipped
                ),
                "agents": [dict(agents_state[aid]) for aid in agent_ids],
                "helm": helm,
                "edges": edges,
                "files": [
                    {
                        "path": primary or primary_file,
                        "status": file_status,
                        "snippet": _snippet_placeholder(snippet_key),
                    }
                ],
                "sourceEventId": f"log-phase-{index}",
            }
        )
        at_ms += 1400

    if guardrails_blocked and frames:
        frames[-1]["narration"] += f" ({guardrails_blocked} guardrail blocks this run.)"

    return frames


def _snippet_placeholder(key: str) -> str:
    """Mirror helm/frontend/src/flightRecorder/snippets.ts for consistent UI."""
    placeholders = {
        "auth_clean": """@router.post("/login")
async def login(...):
    token = auth_service.create_access_token(...)""",
        "auth_agent_a_edit": """@router.post("/login")
async def login(...):
    # agent_a: shorter TTL
    token = auth_service.create_access_token(..., ttl=900)""",
        "auth_agent_b_edit": """@router.post("/login")
async def login(...):
    # agent_b: OAuth branch
    auth_service.validate_oauth_callback(...)""",
        "auth_guardrail_blocked": """# BLOCKED: delete session store
# guardrail prevented destructive write""",
        "cart_conflict": """<<<<<<< agent/agent_a
checkout_total = sum(line.price for line in cart)
=======
checkout_total = cart.subtotal_with_tax()
>>>>>>> agent/agent_b""",
        "cart_merged": """checkout_total = cart.subtotal_with_tax()
# Helm merge: single resolved total""",
    }
    return placeholders.get(key, "# …")


def _build_edges(agents: list[dict], helm: dict) -> list[dict]:
    edges = []
    for agent in agents:
        kind = "idle"
        status = agent["status"]
        if helm.get("active"):
            action = helm.get("action")
            if action == "dedup" and status == "blocked":
                kind = "dedup"
            elif action == "guardrail" and status == "blocked":
                kind = "guardrail"
            elif action == "merge":
                kind = "merge" if status == "conflicted" else "merge"
            elif action == "reassign":
                kind = "reassigned"
            elif status == "coding":
                kind = "coding"
        elif status == "coding":
            kind = "coding"
        elif status == "blocked":
            kind = "blocked"
        elif status == "reassigned":
            kind = "reassigned"
        elif status == "conflicted":
            kind = "conflicted"
        elif status == "complete":
            kind = "complete"
        edges.append(
            {
                "from": "helm",
                "to": agent["id"],
                "kind": kind,
                "label": helm.get("detail") if helm.get("active") else None,
            }
        )
    return edges


def _title_for_step(step: dict) -> str:
    kind = step.get("kind", "")
    if kind == "helm_dedup":
        return "Helm fleet dedup"
    if kind == "helm_merge":
        return "Helm merge fix"
    if kind == "guardrail":
        return f"Guardrail — {step.get('agent_id', 'agent')}"
    if step.get("agent_id") and step.get("task_id"):
        return f"{step['agent_id']} — {step['task_id']} ({kind})"
    return kind or "step"


def _narration_for_step(
    step: dict, *, path_mode: str, gate_skipped: bool | None
) -> str:
    kind = step.get("kind", "")
    if kind == "helm_dedup":
        return "Helm detected duplicate work and trimmed overlap before more edits."
    if kind == "guardrail":
        return "Guardrail blocked a destructive or conflicting write."
    if kind == "edit" and step.get("intent"):
        return step["intent"]
    if kind == "helm_merge":
        if path_mode == "baseline":
            return (
                f"Baseline path: git conflict on {step.get('file', 'file')} — "
                "Haiku merge-fix (no Helm API)."
            )
        return "Helm resolved merge conflict markers with a single arbitration pass."
    if gate_skipped and kind == "edit":
        return f"{step.get('intent', 'Agent edit')} (contention gate allowed — disjoint enough to skip dedup)."
    return step.get("intent") or "Live Bedrock step from matrix run."


def extract_phases(log_text: str, *, app: str, path_mode: str, suite: str, n: int) -> list[str]:
    needle = f"{app} {path_mode} {suite} n{n}"
    phases: list[str] = []
    in_block = False
    for line in log_text.splitlines():
        if needle in line and "phase=" in line:
            in_block = True
            match = PHASE_RE.search(line)
            if match:
                phases.append(match.group("phase"))
            continue
        if in_block and needle not in line and BLOCK_RE.search(line):
            break
        if in_block and line.strip().startswith("ShopFix LIVE") or line.strip().startswith("Streamcast LIVE"):
            break
    # collapse consecutive duplicates
    collapsed: list[str] = []
    for phase in phases:
        if not collapsed or collapsed[-1] != phase:
            collapsed.append(phase)
    return collapsed


def resolve_latest_matrix_json(explicit: Path | None) -> Path:
    if explicit and explicit.is_file():
        return explicit
    results = ROOT / "experiments" / "results"
    candidates = sorted(results.glob("live_matrix_*.json"), key=lambda p: p.stat().st_mtime)
    for path in reversed(candidates):
        if path.name != "live_matrix_checkpoint.json":
            return path
    return ROOT / "experiments/results/live_matrix_checkpoint.json"


def load_matrix_meta(matrix_json: Path, *, app: str, suite: str, n: int, path_mode: str) -> dict:
    if not matrix_json.is_file():
        return {}
    payload = json.loads(matrix_json.read_text(encoding="utf-8"))
    for cell in payload.get("cells") or []:
        if (
            cell.get("app") == app
            and cell.get("suite") == suite
            and cell.get("agent_count") == n
        ):
            path = cell.get(path_mode) or {}
            helm_inner = path.get("helm") or {}
            comparison = cell.get("comparison") or {}
            return {
                "gate_skipped": path.get("gate_skipped"),
                "guardrails_blocked": helm_inner.get("guardrails_blocked"),
                "continuations": path.get("continuations") or [],
                "reassignments": path.get("reassignments") or [],
                "dedup_calls": path.get("dedup_calls"),
                "baseline_cost": comparison.get("baseline_cost_display"),
                "helm_cost": comparison.get("helm_cost_display"),
                "cost_savings_pct": comparison.get("cost_savings_pct"),
                "token_savings_pct": comparison.get("token_savings_pct"),
                "time_savings_pct": comparison.get("time_savings_pct"),
                "baseline_tokens": comparison.get("baseline_total_tokens"),
                "helm_tokens": comparison.get("helm_total_tokens"),
                "helm_gate_skipped": comparison.get("helm_gate_skipped"),
                "helm_dedup_calls": comparison.get("helm_dedup_calls"),
                "generated_at": payload.get("generated_at"),
            }
    return {}


def default_out_path(path_mode: str) -> Path:
    if path_mode == "baseline":
        return ROOT / "frontend/public/traces/contention-n2-live-baseline.json"
    return ROOT / "frontend/public/traces/contention-n2-live.json"


def export_one(args: argparse.Namespace, *, path_mode: str, out: Path) -> int:
    matrix_path = resolve_latest_matrix_json(args.matrix_json)
    if not args.log.is_file():
        print(f"ERROR: log not found: {args.log}", file=sys.stderr)
        return 1

    log_text = args.log.read_text(encoding="utf-8", errors="replace")
    phase_strings = extract_phases(
        log_text,
        app=args.app,
        path_mode=path_mode,
        suite=args.suite,
        n=args.agents,
    )
    if not phase_strings:
        print(
            f"ERROR: no phases for {args.app} {path_mode} {args.suite} n{args.agents}",
            file=sys.stderr,
        )
        return 2

    tasks = load_task_map()
    parsed = [parse_phase(p, tasks) for p in phase_strings]
    meta = load_matrix_meta(
        matrix_path,
        app=args.app,
        suite=args.suite,
        n=args.agents,
        path_mode=path_mode,
    )

    agent_ids = [f"agent_{chr(ord('a') + i)}" for i in range(args.agents)]
    primary_file = "backend/app/routers/auth.py"
    for step in parsed:
        if step.get("file"):
            primary_file = step["file"]
            break

    frames = build_frames(
        parsed,
        agent_ids=agent_ids,
        primary_file=primary_file,
        path_mode=path_mode,
        gate_skipped=meta.get("gate_skipped"),
        guardrails_blocked=meta.get("guardrails_blocked"),
    )

    savings = meta.get("cost_savings_pct")
    tokens = meta.get("token_savings_pct")
    stats = ""
    if savings is not None and tokens is not None:
        stats = f" Measured: {savings}% cost, {tokens}% tokens vs baseline."

    trace = {
        "id": f"{args.suite}_n{args.agents}_live_{path_mode}",
        "label": f"Live · N={args.agents} · {args.suite} ({path_mode})",
        "description": (
            f"Real Bedrock run from {matrix_path.name} — {path_mode} path, "
            f"{len(phase_strings)} timed phases from log.{stats}"
        ),
        "frames": frames,
        "meta": {
            "source_log": str(args.log),
            "source_matrix": str(matrix_path),
            "phase_count": len(phase_strings),
            "path_mode": path_mode,
            **meta,
        },
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(f"Wrote {out} ({len(frames)} frames from {len(phase_strings)} log phases)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Export flight trace JSON from matrix log")
    parser.add_argument("--log", type=Path, default=ROOT / "experiments/results/live_matrix_run.log")
    parser.add_argument(
        "--matrix-json",
        type=Path,
        default=None,
        help="Defaults to newest experiments/results/live_matrix_*.json",
    )
    parser.add_argument("--app", default="shopfix")
    parser.add_argument("--path-mode", default="helm", choices=["baseline", "helm"])
    parser.add_argument("--suite", default="contention")
    parser.add_argument("--agents", type=int, default=2)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Defaults to contention-n2-live.json (helm) or -baseline.json",
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Export helm + baseline traces from the same log/matrix",
    )
    args = parser.parse_args()
    if args.both:
        rc = export_one(
            args,
            path_mode="helm",
            out=args.out or default_out_path("helm"),
        )
        if rc != 0:
            return rc
        return export_one(
            args,
            path_mode="baseline",
            out=default_out_path("baseline"),
        )

    out = args.out or default_out_path(args.path_mode)
    return export_one(args, path_mode=args.path_mode, out=out)


if __name__ == "__main__":
    raise SystemExit(main())
