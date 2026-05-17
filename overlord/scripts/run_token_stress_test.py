#!/usr/bin/env python3
"""Live Bedrock stress test with large prompts (verify billing / token usage)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=True)
    except ImportError:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if value.strip():
                os.environ[key.strip()] = value.strip()


def _padding_block() -> str:
    return (
        "# Commerce platform reference: auth handlers, catalog search, billing invoices.\n"
        "def _reference_login_flow(email: str, password: str) -> dict:\n"
        "    user = db.validate_user(email, password)\n"
        "    token = jwt.encode({'sub': email}, 'secret', algorithm='HS256')\n"
        "    return {'access_token': token, 'user_id': getattr(user, 'id', None)}\n"
        "\n"
        "def _reference_search_products(query: str, limit: int = 20) -> list:\n"
        "    return [p for p in _CATALOG if query.lower() in p.title.lower()][:limit]\n"
    )


def build_large_prompt(target_input_tokens: int) -> str:
    """Approximate token count via chars/4 (close enough for stress sizing)."""
    block = _padding_block()
    chars_per_token = 4
    target_chars = target_input_tokens * chars_per_token
    repeats = max(1, target_chars // len(block))
    body = (block * repeats)[:target_chars]
    return (
        "You are a code reviewer. Summarize the following reference modules in 3 bullet points.\n"
        "Do not reproduce the full text.\n\n"
        f"{body}\n\n"
        "Respond as JSON: {\"summary\": [\"...\", \"...\", \"...\"]}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-input-tokens",
        type=int,
        default=20_000,
        help="Approximate input size before the model call (default 20000)",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=4096,
        help="max_tokens for the completion",
    )
    parser.add_argument(
        "--model",
        choices=("sonnet", "haiku"),
        default="sonnet",
    )
    parser.add_argument(
        "--calls",
        type=int,
        default=1,
        help="Number of sequential Bedrock invocations",
    )
    args = parser.parse_args()

    _load_dotenv()
    if os.getenv("OVERLORD_MOCK_BEDROCK") == "1":
        print("ERROR: OVERLORD_MOCK_BEDROCK=1 — no real AWS spend. Set to 0 in .env", file=sys.stderr)
        return 1

    import boto3
    from bedrock.cost_estimate import estimate_usd, format_usd
    from bedrock.invoke_tracked import invoke_anthropic_messages
    from bedrock.model_ids import resolve_inference_profile_id

    region = os.getenv("AWS_REGION", "us-east-1")
    ident = boto3.client("sts", region_name=region).get_caller_identity()
    print(f"AWS account: {ident['Account']}")
    print(f"ARN: {ident['Arn']}")
    print(f"Region: {region}")
    print(f"Mock: {os.getenv('OVERLORD_MOCK_BEDROCK', '0')}")
    print()

    if args.model == "sonnet":
        model_id = resolve_inference_profile_id(
            os.getenv("OVERLORD_BEDROCK_MODEL_ID")
            or os.getenv("OVERLORD_BEDROCK_MODEL", "us.anthropic.claude-sonnet-4-6")
        )
        role = "stress-sonnet"
    else:
        model_id = resolve_inference_profile_id(
            os.getenv(
                "OVERLORD_AGENT_MODEL_ID",
                "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            )
        )
        role = "stress-haiku"

    prompt = build_large_prompt(args.target_input_tokens)
    est_chars = len(prompt)
    print(f"Prompt chars: {est_chars:,} (~{est_chars // 4:,} tokens heuristic)")
    print(f"Model: {model_id}")
    print(f"max_output_tokens: {args.max_output_tokens}")
    print(f"Calls: {args.calls}")
    print()

    totals = {"input": 0, "output": 0, "latency_ms": 0}
    for i in range(args.calls):
        print(f"--- call {i + 1}/{args.calls} ---")
        text, usage = invoke_anthropic_messages(
            model_id=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=args.max_output_tokens,
            role=role,
        )
        totals["input"] += usage.input_tokens
        totals["output"] += usage.output_tokens
        totals["latency_ms"] += usage.latency_ms
        est = estimate_usd(model_id, usage.input_tokens, usage.output_tokens)
        print(
            f"  input={usage.input_tokens:,} output={usage.output_tokens:,} "
            f"total={usage.total_tokens:,} latency={usage.latency_ms}ms "
            f"est_cost={format_usd(est)}"
        )
        preview = text[:200].replace("\n", " ")
        print(f"  response preview: {preview!r}...")

    total_tok = totals["input"] + totals["output"]
    total_est = estimate_usd(model_id, totals["input"], totals["output"])
    print()
    print("=== totals ===")
    print(json.dumps({**totals, "total_tokens": total_tok, "est_usd": round(total_est, 4)}, indent=2))
    print()
    print(
        "If credits still do not move: check Cost Explorer → Bedrock (filter by this account), "
        "billing lag 24h+, and whether promo credits exclude Bedrock."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
