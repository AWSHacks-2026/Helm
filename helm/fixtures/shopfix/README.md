# ShopFix

Small Etsy-style marketplace fixture for Helm git benchmarks and judge demos.

## Quick start

```bash
# Backend API (port 8001)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# Frontend (port 5173) — after Task 7
cd frontend && npm ci && npm run dev
```

## Verify

```bash
./scripts/verify_shopfix.sh
```

## Layout

- `backend/` — FastAPI + SQLite (auth, listings, cart, checkout)
- `frontend/` — Vite + React storefront
- `scenarios/` — benchmark agent assignments (M2)
- `patches/` — deterministic agent diffs (M2)
