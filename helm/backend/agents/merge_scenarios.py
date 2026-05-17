"""Hardcoded merge-conflict scenarios for agent testing and A/B vs naive baselines."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# Acceptance heuristics: substring checks on resolved_code (case-insensitive).
AcceptanceCriteria = dict[str, Any]

MERGE_SCENARIO_META: dict[str, dict[str, str]] = {
    "merge_conflict": {
        "kind": "merge",
        "title": "get_user — cache vs type hints",
        "description": "Agent A adds caching; Agent B adds types and drops cache.",
    },
    "merge_rate_limit": {
        "kind": "merge",
        "title": "rate_limit — sync sleep vs async",
        "description": "Agent A uses time.sleep; Agent B rewrites with asyncio.",
    },
    "merge_error_handler": {
        "kind": "merge",
        "title": "fetch — bare except vs typed errors",
        "description": "Agent A swallows all errors; Agent B handles specific exceptions.",
    },
    "merge_config_loader": {
        "kind": "merge",
        "title": "load_config — os.environ vs YAML file",
        "description": "Agent A reads env vars; Agent B loads settings.yaml.",
    },
    "merge_conflict_fleet": {
        "kind": "merge",
        "title": "Commerce platform — six-agent merge conflicts",
        "description": "Six agents produce conflicting code on auth, catalog, and billing modules.",
    },
}

MERGE_SCENARIOS: dict[str, dict[str, Any]] = {
    "merge_conflict": {
        "file_path": "app/services/user.py",
        "agent_a": {
            "intent": "I am optimizing this function for speed using caching",
            "code": """
def get_user(user_id):
    if user_id in cache:
        return cache[user_id]
    result = db.query(user_id)
    cache[user_id] = result
    return result
""".strip(),
        },
        "agent_b": {
            "intent": "I am refactoring this function for readability and adding type hints",
            "code": """
def get_user(user_id: str) -> User:
    return db.query(user_id)
""".strip(),
        },
        "acceptance": {
            "must_include": ["get_user", "cache", "user_id"],
            "must_include_any": [["str", "User"], ["->"]],
            "must_not_equal_agent": True,
        },
    },
    "merge_rate_limit": {
        "file_path": "app/middleware/rate_limit.py",
        "agent_a": {
            "intent": "I am adding a simple synchronous rate limiter with sleep backoff",
            "code": """
import time

def rate_limit(key: str, limit: int = 10) -> bool:
    count = _counts.get(key, 0)
    if count >= limit:
        time.sleep(0.5)
        return False
    _counts[key] = count + 1
    return True
""".strip(),
        },
        "agent_b": {
            "intent": "I am converting rate limiting to async for the FastAPI stack",
            "code": """
import asyncio

async def rate_limit(key: str, limit: int = 10) -> bool:
    async with _locks[key]:
        count = _counts.get(key, 0)
        if count >= limit:
            await asyncio.sleep(0.1)
            return False
        _counts[key] = count + 1
        return True
""".strip(),
        },
        "acceptance": {
            "must_include": ["rate_limit", "limit"],
            "must_include_any": [["async"], ["await"]],
            "must_not_equal_agent": True,
        },
    },
    "merge_error_handler": {
        "file_path": "app/clients/http.py",
        "agent_a": {
            "intent": "I am making fetch resilient by catching any failure",
            "code": """
def fetch(url: str) -> dict:
    try:
        return requests.get(url, timeout=5).json()
    except Exception:
        return {}
""".strip(),
        },
        "agent_b": {
            "intent": "I am tightening error handling to specific HTTP and timeout errors",
            "code": """
def fetch(url: str) -> dict:
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except (requests.HTTPError, requests.Timeout) as exc:
        raise ApiError(str(exc)) from exc
""".strip(),
        },
        "acceptance": {
            "must_include": ["fetch", "timeout"],
            "must_include_any": [["HTTPError", "Timeout"], ["ApiError"]],
            "must_not_equal_agent": True,
        },
    },
    "merge_config_loader": {
        "file_path": "app/config.py",
        "agent_a": {
            "intent": "I am loading configuration from environment variables for 12-factor deploys",
            "code": """
import os

def load_config() -> dict:
    return {
        "database_url": os.environ["DATABASE_URL"],
        "debug": os.environ.get("DEBUG", "0") == "1",
    }
""".strip(),
        },
        "agent_b": {
            "intent": "I am loading configuration from settings.yaml for local dev parity",
            "code": """
import yaml

def load_config() -> dict:
    with open("settings.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
""".strip(),
        },
        "acceptance": {
            "must_include": ["load_config"],
            "must_include_any": [["environ", "DATABASE_URL"], ["yaml", "settings.yaml"]],
            "must_not_equal_agent": True,
        },
    },
    "merge_conflict_fleet": {
        "title": "Commerce Platform — Six Agent Merge Conflicts",
        "file_paths": {
            "agent_a": "app/auth/handlers.py",
            "agent_b": "app/auth/handlers.py",
            "agent_c": "app/auth/handlers.py",
            "agent_d": "app/catalog/products.py",
            "agent_e": "app/catalog/products.py",
            "agent_f": "app/billing/invoices.py",
        },
        "agents": {
            "agent_a": {
                "intent": "JWT login with in-memory token cache for fast auth",
                "code": '''
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt

router = APIRouter(prefix="/auth")
_token_cache: dict[str, str] = {}

class LoginBody(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(body: LoginBody) -> dict:
    if body.email in _token_cache:
        return {"access_token": _token_cache[body.email]}
    token = jwt.encode({"sub": body.email}, "secret", algorithm="HS256")
    _token_cache[body.email] = token
    return {"access_token": token}
'''.strip(),
            },
            "agent_b": {
                "intent": "Typed sign-in without caching — direct DB validation",
                "code": '''
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth")

class LoginBody(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
def login(body: LoginBody) -> dict:
    user = db.validate_user(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"ok": True, "user_id": user.id}
'''.strip(),
            },
            "agent_c": {
                "intent": "Session-cookie auth instead of bearer tokens",
                "code": '''
from fastapi import APIRouter, Response
from pydantic import BaseModel

router = APIRouter(prefix="/auth")
_sessions: dict[str, str] = {}

class LoginBody(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(body: LoginBody, response: Response) -> dict:
    session_id = f"sess_{body.email}"
    _sessions[session_id] = body.email
    response.set_cookie("session_id", session_id, httponly=True)
    return {"session": session_id}
'''.strip(),
            },
            "agent_d": {
                "intent": "Product search with text filters and pagination",
                "code": '''
from dataclasses import dataclass

@dataclass
class Product:
    sku: str
    title: str
    price_cents: int

def search_products(query: str, limit: int = 20, offset: int = 0) -> list[Product]:
  results = [p for p in _CATALOG if query.lower() in p.title.lower()]
  return results[offset : offset + limit]
'''.strip(),
            },
            "agent_e": {
                "intent": "Product listing sorted by price with category filter",
                "code": '''
from dataclasses import dataclass

@dataclass
class Product:
    sku: str
    title: str
    price_cents: int
    category: str

def list_products(category: str | None = None, sort: str = "price") -> list[Product]:
    items = list(_CATALOG)
    if category:
        items = [p for p in items if p.category == category]
    return sorted(items, key=lambda p: p.price_cents)
'''.strip(),
            },
            "agent_f": {
                "intent": "Invoice totals with tax lines",
                "code": '''
from dataclasses import dataclass, field

@dataclass
class InvoiceLine:
    description: str
    amount_cents: int

@dataclass
class Invoice:
    customer_id: str
    lines: list[InvoiceLine] = field(default_factory=list)
    tax_rate: float = 0.08

    def total_cents(self) -> int:
        subtotal = sum(line.amount_cents for line in self.lines)
        return int(subtotal * (1 + self.tax_rate))
'''.strip(),
            },
        },
        "acceptance_by_file": {
            "app/auth/handlers.py": {
                "must_include": ["router", "login", "def"],
                "must_include_any": [["jwt", "token"], ["session", "cookie"]],
                "must_not_equal_agent": True,
            },
            "app/catalog/products.py": {
                "must_include": ["Product", "def"],
                "must_include_any": [["search"], ["list", "sort"]],
                "must_not_equal_agent": True,
            },
            "app/billing/invoices.py": {
                "must_include": ["Invoice", "total", "def"],
                "must_not_equal_agent": False,
            },
        },
    },
}

# Deterministic mock resolutions when HELM_MOCK_BEDROCK=1 (merge lab + smoke).
MERGE_MOCK_RESOLUTIONS: dict[str, dict[str, str]] = {
    "merge_conflict": {
        "conflict_type": "merge_conflict",
        "reasoning": "MOCK: Combined Agent A caching with Agent B type hints.",
        "resolved_code": (
            "def get_user(user_id: str) -> User:\n"
            "    if user_id in cache:\n"
            "        return cache[user_id]\n"
            "    result = db.query(user_id)\n"
            "    cache[user_id] = result\n"
            "    return result\n"
        ),
        "tokens_saved_estimate": "~2400 (mock)",
    },
    "merge_rate_limit": {
        "conflict_type": "merge_conflict",
        "reasoning": "MOCK: Async rate_limit with bounded backoff instead of blocking sleep.",
        "resolved_code": (
            "import asyncio\n\n"
            "async def rate_limit(key: str, limit: int = 10) -> bool:\n"
            "    async with _locks[key]:\n"
            "        count = _counts.get(key, 0)\n"
            "        if count >= limit:\n"
            "            await asyncio.sleep(0.1)\n"
            "            return False\n"
            "        _counts[key] = count + 1\n"
            "        return True\n"
        ),
        "tokens_saved_estimate": "~1800 (mock)",
    },
    "merge_error_handler": {
        "conflict_type": "merge_conflict",
        "reasoning": "MOCK: Specific HTTP/timeout handling without bare except.",
        "resolved_code": (
            "def fetch(url: str) -> dict:\n"
            "    try:\n"
            "        response = requests.get(url, timeout=5)\n"
            "        response.raise_for_status()\n"
            "        return response.json()\n"
            "    except (requests.HTTPError, requests.Timeout) as exc:\n"
            "        raise ApiError(str(exc)) from exc\n"
        ),
        "tokens_saved_estimate": "~2100 (mock)",
    },
    "merge_config_loader": {
        "conflict_type": "merge_conflict",
        "reasoning": "MOCK: Env vars override YAML defaults for production.",
        "resolved_code": (
            "import os\nimport yaml\n\n"
            "def load_config() -> dict:\n"
            "    with open('settings.yaml', encoding='utf-8') as fh:\n"
            "        base = yaml.safe_load(fh) or {}\n"
            "    base['database_url'] = os.environ.get('DATABASE_URL', base.get('database_url'))\n"
            "    base['debug'] = os.environ.get('DEBUG', str(base.get('debug', False))) == '1'\n"
            "    return base\n"
        ),
        "tokens_saved_estimate": "~1900 (mock)",
    },
}


def get_merge_scenario_names() -> list[str]:
    return list(MERGE_SCENARIOS.keys())


def get_pairwise_merge_scenario_names() -> list[str]:
    """Two-agent scenarios for live_harness (excludes fleet)."""
    return [name for name in MERGE_SCENARIOS if "file_path" in MERGE_SCENARIOS[name]]


def get_merge_scenario(name: str) -> dict[str, Any]:
    if name not in MERGE_SCENARIOS:
        raise KeyError(name)
    return deepcopy(MERGE_SCENARIOS[name])


def get_merge_meta() -> list[dict[str, str]]:
    return [
        {"name": name, **meta}
        for name, meta in MERGE_SCENARIO_META.items()
    ]
