import json

import boto3
from moto import mock_aws

from bedrock import knowledge_base as kb


@mock_aws
def test_sync_session_to_s3(monkeypatch):
    bucket = "overlord-demo-logs"
    monkeypatch.setenv("OVERLORD_S3_BUCKET", bucket)
    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket=bucket)

    kb.log_action("agent_a", "add_file", "utils/cache.py", "Added cache")
    key = kb.sync_to_s3()
    assert key.endswith(".json")

    obj = conn.get_object(Bucket=bucket, Key=key)
    body = json.loads(obj["Body"].read())
    assert len(body) == 1
