#!/usr/bin/env python3
"""Verify AWS credentials and optional Helm cloud resources."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from bedrock.model_ids import DEFAULT_HELM_BEDROCK_MODEL_ID, resolve_inference_profile_id


def _bedrock_model_id() -> str:
    return resolve_inference_profile_id(
        os.getenv("HELM_BEDROCK_MODEL_ID")
        or os.getenv("HELM_BEDROCK_MODEL")
        or DEFAULT_HELM_BEDROCK_MODEL_ID
    )


def _agent_model_id() -> str:
    return resolve_inference_profile_id(
        os.getenv(
            "HELM_AGENT_MODEL_ID",
            "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        )
    )


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=True)
        return
    except ImportError:
        pass
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not value:
            continue
        os.environ[key] = value


def check_credentials() -> dict:
    import boto3
    from botocore.exceptions import MissingDependencyException, NoCredentialsError

    for blank in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        if os.environ.get(blank) == "":
            del os.environ[blank]

    try:
        sts = boto3.client("sts", region_name=os.getenv("AWS_REGION", "us-east-1"))
        ident = sts.get_caller_identity()
    except MissingDependencyException as exc:
        return {
            "name": "aws_credentials",
            "passed": False,
            "detail": (
                f"{exc}. Run: pip install 'botocore[crt]'  (required for aws login)"
            ),
        }
    except NoCredentialsError:
        return {
            "name": "aws_credentials",
            "passed": False,
            "detail": "No credentials. Run: aws login  (or aws configure)",
        }
    except Exception as exc:  # noqa: BLE001
        return {"name": "aws_credentials", "passed": False, "detail": str(exc)}

    return {
        "name": "aws_credentials",
        "passed": True,
        "detail": ident.get("Arn", ident.get("Account", "")),
    }


def _invoke_probe(model_id: str) -> tuple[bool, str]:
    import boto3

    region = os.getenv("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 32,
        "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
    }
    resp = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    payload = json.loads(resp["body"].read())
    text = payload.get("content", [{}])[0].get("text", "")
    return bool(text), text[:80]


def _bedrock_hint(msg: str, model_id: str) -> str:
    hint = ""
    if "inference profile" in msg.lower() or "on-demand throughput" in msg.lower():
        hint = (
            f" Use inference profile ID (e.g. us.anthropic.claude-sonnet-4-6). "
            f"Tried: {model_id}"
        )
    elif "Legacy" in msg or "ResourceNotFound" in msg or "use case" in msg.lower():
        hint = (
            " Enable Claude Sonnet 4.6 in Bedrock → Model access (us-east-1) and set "
            "HELM_BEDROCK_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0 in helm/.env. "
            f"Tried: {model_id}"
        )
    return hint


def check_bedrock_invoke() -> dict:
    if os.getenv("HELM_MOCK_BEDROCK") == "1":
        return {
            "name": "bedrock_invoke",
            "passed": True,
            "detail": "skipped (HELM_MOCK_BEDROCK=1)",
        }
    model_id = _bedrock_model_id()
    try:
        ok, text = _invoke_probe(model_id)
        return {
            "name": "bedrock_invoke",
            "passed": ok,
            "detail": f"{model_id}: {text}",
        }
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        return {
            "name": "bedrock_invoke",
            "passed": False,
            "detail": msg + _bedrock_hint(msg, model_id),
        }


def check_bedrock_agent_invoke() -> dict:
    if os.getenv("HELM_MOCK_BEDROCK") == "1":
        return {
            "name": "bedrock_agent_invoke",
            "passed": True,
            "detail": "skipped (HELM_MOCK_BEDROCK=1)",
        }
    model_id = _agent_model_id()
    try:
        ok, text = _invoke_probe(model_id)
        return {
            "name": "bedrock_agent_invoke",
            "passed": ok,
            "detail": f"{model_id}: {text}",
        }
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        return {
            "name": "bedrock_agent_invoke",
            "passed": False,
            "detail": msg + _bedrock_hint(msg, model_id),
        }


def check_memory() -> dict:
    memory_id = os.getenv("AGENTCORE_MEMORY_ID", "").strip()
    use_local = os.getenv("HELM_USE_LOCAL_MEMORY", "true").lower() == "true"
    if use_local or not memory_id:
        return {
            "name": "agentcore_memory",
            "passed": True,
            "detail": "local mode (set AGENTCORE_MEMORY_ID + HELM_USE_LOCAL_MEMORY=false to test cloud)",
        }
    try:
        from bedrock import agentcore_memory as mem

        mem.log_intent("verify-aws", "agent_a", "probe intent", "README.md")
        events = mem.list_events("verify-aws", limit=5)
        return {
            "name": "agentcore_memory",
            "passed": len(events) >= 1,
            "detail": f"{len(events)} event(s) for session verify-aws",
        }
    except Exception as exc:  # noqa: BLE001
        return {"name": "agentcore_memory", "passed": False, "detail": str(exc)}


def check_policy_env() -> dict:
    engine_id = os.getenv("AGENTCORE_POLICY_ENGINE_ID", "").strip()
    use_local = os.getenv("HELM_USE_LOCAL_POLICY", "true").lower() == "true"
    if use_local:
        detail = "local bridge (Python Cedar semantics)"
    elif engine_id:
        detail = f"engine {engine_id} configured (Gateway ENFORCE optional)"
    else:
        detail = "HELM_USE_LOCAL_POLICY=false but no AGENTCORE_POLICY_ENGINE_ID"
    passed = use_local or bool(engine_id)
    return {"name": "agentcore_policy", "passed": passed, "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bedrock", action="store_true", help="Require Bedrock invoke check")
    parser.add_argument("--memory", action="store_true", help="Require cloud memory check")
    args = parser.parse_args()

    _load_dotenv()
    checks = [check_credentials(), check_policy_env()]
    if args.bedrock or os.getenv("HELM_MOCK_BEDROCK", "0") != "1":
        checks.append(check_bedrock_invoke())
        checks.append(check_bedrock_agent_invoke())
    if args.memory:
        os.environ["HELM_USE_LOCAL_MEMORY"] = "false"
        checks.append(check_memory())
    else:
        checks.append(check_memory())

    all_passed = all(c["passed"] for c in checks)
    print(json.dumps({"all_passed": all_passed, "checks": checks}, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
