"""Run multi-agent experiments without Overlord arbitration."""

from __future__ import annotations

import ast
import time
from pathlib import Path
from typing import Any

import yaml

from agents.haiku_agent import run_agent_edit
from experiments.metrics import AgentRunResult, ThemeRunResult

EXPERIMENTS_ROOT = Path(__file__).resolve().parent


def load_manifest(theme_dir: Path) -> dict[str, Any]:
    manifest_path = theme_dir / "manifest.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid manifest: {manifest_path}")
    return data


def load_base_files(theme_dir: Path, manifest: dict[str, Any]) -> dict[str, str]:
    base_dir = theme_dir / manifest["base_dir"]
    files: dict[str, str] = {}
    for assignment in manifest.get("assignments", []):
        for fp in assignment.get("files", []):
            rel = fp.replace("\\", "/")
            path = base_dir / rel
            if path.is_file():
                files[rel] = path.read_text(encoding="utf-8")
    return files


def _mock_agent_code(agent_id: str, feature: str, base: str) -> str:
    """Valid Python that diverges per agent (cheap, deterministic)."""
    tag = agent_id.replace("agent_", "")
    suffix = hash(agent_id) % 3
    if suffix == 0:
        extra = f"\n\n# {tag}: in-memory cache path\n_LOOKUP_CACHE: dict[str, dict] = {{}}\n"
    elif suffix == 1:
        extra = (
            f"\n\n# {tag}: disk cache path\n"
            "import json\nfrom pathlib import Path\n"
            "_CACHE_FILE = Path('.cache') / 'data.json'\n"
        )
    else:
        extra = f"\n\n# {tag}: feature branch\n_FEATURE_FLAG_{tag.upper()} = True\n"
    return base.rstrip() + extra


def run_theme(
    theme_dir: Path,
    *,
    mock: bool = False,
) -> ThemeRunResult:
    manifest = load_manifest(theme_dir)
    base_files = load_base_files(theme_dir, manifest)
    assignments = manifest["assignments"]
    agent_runs: list[AgentRunResult] = []
    outputs_by_file: dict[str, dict[str, str]] = {}

    for assignment in assignments:
        agent_id = assignment["id"]
        feature = assignment["feature"].strip()
        for file_rel in assignment["files"]:
            file_path = file_rel.replace("\\", "/")
            base_code = base_files.get(file_path, "")
            peer_code = None
            if file_path in outputs_by_file:
                peers = outputs_by_file[file_path]
                if peers:
                    peer_code = next(iter(peers.values()))

            started = time.perf_counter()
            if mock:
                code = _mock_agent_code(agent_id, feature, base_code)
                usage_in, usage_out = 120, 180
                elapsed_ms = max(1, int((time.perf_counter() - started) * 1000))
            else:
                intent = feature
                if base_code:
                    intent = f"{feature}\n\nCurrent file:\n```python\n{base_code}\n```"
                code, usage = run_agent_edit(
                    agent_id=agent_id,
                    file_path=file_path,
                    intent=intent,
                    peer_code=peer_code,
                )
                usage_in = usage.input_tokens
                usage_out = usage.output_tokens
                elapsed_ms = int((time.perf_counter() - started) * 1000)

            outputs_by_file.setdefault(file_path, {})[agent_id] = code
            agent_runs.append(
                AgentRunResult(
                    agent_id=agent_id,
                    file_path=file_path,
                    code=code,
                    elapsed_ms=elapsed_ms,
                    input_tokens=usage_in,
                    output_tokens=usage_out,
                    syntax_ok=_syntax_ok(code),
                )
            )

    return ThemeRunResult(
        theme_name=manifest["name"],
        assignments=assignments,
        agent_runs=agent_runs,
        base_files=base_files,
    )


def run_all_themes(
    themes_parent: Path | None = None,
    *,
    theme_names: list[str] | None = None,
    mock: bool = False,
) -> list[ThemeRunResult]:
    root = themes_parent or (EXPERIMENTS_ROOT / "themes")
    if not root.is_dir():
        return []
    names = theme_names
    if names is None:
        names = sorted(
            p.name
            for p in root.iterdir()
            if p.is_dir() and (p / "manifest.yaml").is_file()
        )
    return [run_theme(root / name, mock=mock) for name in names]


def _syntax_ok(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False
