import os

import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")


def get_bedrock_client():
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=REGION,
    )


def get_bedrock_runtime_client():
    return get_bedrock_client()


def get_bedrock_agent_client():
    return boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=REGION,
    )
