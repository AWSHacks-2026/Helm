import os

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


def _aws_config() -> dict:
    use_local_memory = os.getenv("OVERLORD_USE_LOCAL_MEMORY", "true").lower() == "true"
    use_local_policy = os.getenv("OVERLORD_USE_LOCAL_POLICY", "true").lower() == "true"
    return {
        "region": os.getenv("AWS_REGION", "us-east-1"),
        "bedrock_mock": os.getenv("OVERLORD_MOCK_BEDROCK", "0") == "1",
        "memory_mode": "local" if use_local_memory else "agentcore",
        "policy_mode": "local_bridge" if use_local_policy else "agentcore_engine",
        "agentcore_memory_id_set": bool(os.getenv("AGENTCORE_MEMORY_ID", "").strip()),
        "agentcore_policy_engine_id_set": bool(
            os.getenv("AGENTCORE_POLICY_ENGINE_ID", "").strip()
        ),
    }


@router.get("/")
def root():
    return RedirectResponse(url="/docs")


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "overlord",
        "demo_smoke": "/demo/smoke",
        "merge_lab": "/merge/scenarios",
        "live_benchmark": "/live/benchmark/scenarios",
        "scenarios": "/scenarios",
        "aws": _aws_config(),
    }
