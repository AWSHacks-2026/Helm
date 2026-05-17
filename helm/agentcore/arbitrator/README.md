# Helm Arbitrator — AgentCore Runtime

## Local dev

From repo root, with AWS credentials and Bedrock model access:

```bash
cd helm
source .venv/bin/activate
pip install bedrock-agentcore
export PYTHONPATH=backend
cd agentcore/arbitrator
python main.py
```

In another terminal:

```bash
curl -s -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d @sample_invoke_payload.json
```

**Deployed runtime (CLI):** `--json` is output-only. Use a payload file:

```bash
agentcore invoke --runtime HelmArbitrator --prompt-file sample_invoke_payload.json
```

## Deploy

Prerequisites: `aws login` (or AWS credentials), Node 20+, `npm install -g @aws/agentcore`.

1. **Deployment target** — `helm/agentcore/aws-targets.json` must list your AWS account and region:

```json
[
  {
    "name": "default",
    "account": "YOUR_12_DIGIT_ACCOUNT_ID",
    "region": "us-east-1"
  }
]
```

Get account ID: `aws sts get-caller-identity --query Account --output text`

2. **CDK deps** (once):

```bash
cd helm/agentcore/cdk && npm install
```

3. **Deploy** (from project root `helm/`, not `arbitrator/`):

```bash
cd helm
agentcore deploy
```

4. Set `HELM_ARBITRATOR_ARN` in `helm/.env` from deploy output (`agentcore fetch` also shows ARNs).
