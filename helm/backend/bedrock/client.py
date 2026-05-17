import os

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

_BEDROCK_CONFIG = Config(
    retries={
        "max_attempts": max(1, int(os.getenv("HELM_BEDROCK_BOTO_MAX_ATTEMPTS", "12"))),
        "mode": os.getenv("HELM_BEDROCK_BOTO_RETRY_MODE", "adaptive"),
    },
)


def get_bedrock_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=REGION,
        config=_BEDROCK_CONFIG,
    )


def get_bedrock_runtime_client():
    return get_bedrock_client()


def get_bedrock_agent_client():
    return boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=REGION,
    )
