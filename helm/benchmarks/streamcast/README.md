# Streamcast

Twitch-like demo app for Helm real-agent benchmarks. Modules (`auth`, `streams`, `player`, `chat`) map to independent agent assignments; `app/streams/live.py` is the conflicting hot spot.

## Run locally

```bash
cd helm/benchmarks/streamcast
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8090
```

## Tests

```bash
pytest -v
```
