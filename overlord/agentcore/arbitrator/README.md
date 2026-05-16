# Overlord Arbitrator — AgentCore Runtime

## Local dev

From repo root, with AWS credentials and Bedrock model access:

```bash
cd overlord
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
  -d '{"agent_a":{"intent":"cache","code":"def f(): pass"},"agent_b":{"intent":"types","code":"def f(x: int): pass"}}'
```

## Deploy

```bash
npm install -g @aws/agentcore
cd overlord/agentcore/arbitrator
agentcore create   # if agentcore.json missing
agentcore deploy
```

Set `OVERLORD_ARBITRATOR_ARN` in `overlord/.env` from deploy output.
