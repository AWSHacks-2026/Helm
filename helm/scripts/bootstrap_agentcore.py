#!/usr/bin/env python3
"""Create AgentCore Memory and/or Policy Engine resources for Helm."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CEDAR_PATH = ROOT / "backend" / "bedrock" / "policies" / "helm_coordination.cedar"
REGION = os.getenv("AWS_REGION", "us-east-1")
# AgentCore resource names: [a-zA-Z][a-zA-Z0-9_]{0,47} (no hyphens)
_NAME_RE = re.compile(r"[^a-zA-Z0-9_]")


def _sanitize_name(prefix: str, suffix: str) -> str:
    base = _NAME_RE.sub("_", f"{prefix}_{suffix}".strip("_"))
    if not base or not base[0].isalpha():
        base = f"helm_{base}" if base else "helm_resource"
    return base[:48]


def _control_client():
    import boto3

    return boto3.client("bedrock-agentcore-control", region_name=REGION)


def create_memory(name: str) -> str:
    from bedrock_agentcore.memory import MemoryClient

    client = MemoryClient(region_name=REGION)
    if hasattr(client, "create_memory_and_wait"):
        resp = client.create_memory_and_wait(
            name=name,
            description="Helm multi-agent session history (intents, actions, decisions)",
        )
    else:
        resp = client.create_memory(
            name=name,
            description="Helm multi-agent session history (intents, actions, decisions)",
        )
        memory_id = resp.get("memoryId") or resp.get("id") or resp.get("memory", {}).get("id")
        if memory_id and hasattr(client, "wait_for_memories"):
            client.wait_for_memories(memory_ids=[str(memory_id)])
    memory_id = resp.get("memoryId") or resp.get("id") or resp.get("memory", {}).get("id")
    if not memory_id:
        raise RuntimeError(f"Unexpected create_memory response: {resp}")
    return str(memory_id)


def wait_policy_engine(client, engine_id: str, timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get_policy_engine(policyEngineId=engine_id)
        status = (resp.get("policyEngine") or resp).get("status", "ACTIVE")
        if status in {"ACTIVE", "READY", "AVAILABLE"}:
            return
        if status in {"FAILED", "DELETE_FAILED"}:
            raise RuntimeError(f"Policy engine failed: {resp}")
        time.sleep(3)
    raise TimeoutError(f"Policy engine {engine_id} not ready after {timeout}s")


def create_policy_engine(name: str) -> str:
    client = _control_client()
    token = str(uuid.uuid4())
    resp = client.create_policy_engine(
        name=name,
        description="Helm coordination: file overlap, intent clash, reverse peer work",
        clientToken=token,
    )
    engine = resp.get("policyEngine") or resp
    engine_id = engine.get("policyEngineId") or engine.get("id")
    if not engine_id:
        raise RuntimeError(f"Unexpected create_policy_engine response: {resp}")
    wait_policy_engine(client, engine_id)
    return str(engine_id)


def _cedar_statements() -> list[str]:
    lines = [
        line
        for line in CEDAR_PATH.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("//")
    ]
    body = "\n".join(lines)
    return [block.strip() + ";" for block in body.split(";") if block.strip()]


def upload_cedar_policies(engine_id: str) -> list[str]:
    client = _control_client()
    blocks = _cedar_statements()
    created: list[str] = []
    for idx, block in enumerate(blocks):
        statement = block if block.endswith(";") else f"{block};"
        policy_name = f"helm_coordination_{idx}"
        client.create_policy(
            name=policy_name,
            policyEngineId=engine_id,
            validationMode="IGNORE_ALL_FINDINGS",
            description=f"Helm coordination rule {idx}",
            definition={"cedar": {"statement": statement}},
            clientToken=str(uuid.uuid4()),
        )
        created.append(policy_name)
    return created


def print_env_snippet(memory_id: str | None, engine_id: str | None) -> None:
    lines = ["# Paste into helm/.env", f"AWS_REGION={REGION}"]
    if memory_id:
        lines.extend(
            [
                f"AGENTCORE_MEMORY_ID={memory_id}",
                "HELM_USE_LOCAL_MEMORY=false",
            ]
        )
    if engine_id:
        lines.extend(
            [
                f"AGENTCORE_POLICY_ENGINE_ID={engine_id}",
                "HELM_USE_LOCAL_POLICY=false",
            ]
        )
    lines.append("HELM_MOCK_BEDROCK=0")
    print("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-only", action="store_true")
    parser.add_argument("--policy-only", action="store_true")
    parser.add_argument("--name-prefix", default="helm_hackathon")
    parser.add_argument(
        "--skip-policies",
        action="store_true",
        help="Create policy engine only; skip Cedar upload (needs Gateway ARN)",
    )
    args = parser.parse_args()

    do_memory = not args.policy_only
    do_policy = not args.memory_only

    memory_id: str | None = None
    engine_id: str | None = None

    if do_memory:
        mem_name = _sanitize_name(args.name_prefix, "memory")
        print(f"Creating AgentCore Memory ({mem_name})...", file=sys.stderr)
        memory_id = create_memory(mem_name)
        print(f"  memory_id={memory_id}", file=sys.stderr)

    if do_policy:
        policy_name = _sanitize_name(args.name_prefix, "policy")
        print(f"Creating Policy Engine ({policy_name})...", file=sys.stderr)
        engine_id = create_policy_engine(policy_name)
        print(f"  policy_engine_id={engine_id}", file=sys.stderr)
        if not args.skip_policies:
            print("Uploading Cedar policies...", file=sys.stderr)
            try:
                names = upload_cedar_policies(engine_id)
                print(f"  policies={names}", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001
                print(
                    f"  Cedar upload skipped: {exc}\n"
                    "  Policies need a Gateway ARN in `resource` (see docs/AWS_SETUP.md Tier 4).\n"
                    "  Engine is created — set AGENTCORE_POLICY_ENGINE_ID; rules still run via local bridge.",
                    file=sys.stderr,
                )

    print_env_snippet(memory_id, engine_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"bootstrap failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
