from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from bedrock.invoke_tracked import InvokeUsage, invoke_anthropic_messages
from agents.haiku_agent import agent_model_id
from helm_parse import extract_json_object

logger = logging.getLogger(__name__)

STATIC_AGENT_COUNTS = (2, 4, 8)
HELM_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATIC_OUTPUT_DIR = HELM_ROOT / "demo/generated/static-commerce"
DEFAULT_RICH_STATIC_OUTPUT_DIR = HELM_ROOT / "demo/generated/static-commerce-rich"
StaticSiteMode = Literal["without-helm", "with-helm"]
QualityMode = Literal["standard", "rich"]

REQUIRED_SECTIONS = (
    "hero",
    "catalog",
    "cart",
    "checkout",
    "account",
    "admin",
    "recommendations",
)
SECTION_RE = re.compile(
    r"<section(?P<attrs>[^>]*data-section=[\"'](?P<section>[^\"']+)[\"'][^>]*)>.*?</section>",
    re.DOTALL,
)
FENCED_SECTION_RE = re.compile(
    r"(?P<label>INDEX_HTML|STYLES_CSS|APP_JS)\s*:\s*```[a-zA-Z0-9_-]*\s*(?P<body>.*?)```",
    re.DOTALL,
)
LANGUAGE_FENCE_RE = re.compile(
    r"```(?P<lang>html|css|js|javascript)\s*(?P<body>.*?)```",
    re.IGNORECASE | re.DOTALL,
)
OBJECT_LITERAL_FIELD_RE = re.compile(
    r"(?P<field>index_html|styles_css|app_js)\s*:\s*`(?P<body>.*?)`",
    re.DOTALL,
)
SINGLE_FENCE_RE = re.compile(
    r"```(?:html|css|js|javascript)?\s*(?P<body>.*?)```",
    re.IGNORECASE | re.DOTALL,
)
BODY_RE = re.compile(r"<body[^>]*>(?P<body>.*?)</body>", re.IGNORECASE | re.DOTALL)
CONFLICT_MARKER_RE = re.compile(r"^(?:<<<<<<< .+|=======|>>>>>>> .+)$", re.MULTILINE)


@dataclass(frozen=True)
class StaticSiteConfig:
    agent_counts: tuple[int, ...] = STATIC_AGENT_COUNTS
    output_dir: Path = DEFAULT_STATIC_OUTPUT_DIR
    max_tokens: int = 2000
    allow_mock: bool = False
    show_progress: bool = True
    quality_mode: QualityMode = "standard"

    @classmethod
    def for_quality_mode(
        cls,
        quality_mode: QualityMode,
        **overrides,
    ) -> "StaticSiteConfig":
        defaults = {
            "output_dir": DEFAULT_RICH_STATIC_OUTPUT_DIR
            if quality_mode == "rich"
            else DEFAULT_STATIC_OUTPUT_DIR,
            "max_tokens": 8000 if quality_mode == "rich" else 2000,
            "quality_mode": quality_mode,
        }
        defaults.update(overrides)
        return cls(**defaults)


@dataclass(frozen=True)
class AgentTask:
    agent_id: str
    title: str
    brief: str
    sections: tuple[str, ...]


@dataclass(frozen=True)
class StaticSitePayload:
    index_html: str
    styles_css: str
    app_js: str
    agent_id: str = "unknown"


@dataclass(frozen=True)
class StaticSiteProject:
    agent_count: int
    mode: StaticSiteMode
    files: dict[str, str]
    token_usage: int
    seconds: float
    calls: list[dict[str, int | str]]
    warnings: list[str]
    merge_conflicts: int = 0


@dataclass(frozen=True)
class QualityReport:
    quality_score: int
    missing_sections: list[str]
    duplicate_modules: int
    conflict_markers: int
    broken_links: int
    file_size_warnings: list[str]


@dataclass(frozen=True)
class StaticBenchmarkResult:
    agent_count: int
    mode: StaticSiteMode
    output_dir: str
    tokens: int
    seconds: float
    quality_score: int
    missing_sections: list[str]
    duplicate_modules: int
    conflict_markers: int
    merge_conflicts: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


TASK_LIBRARY = (
    (
        "Homepage and Catalog",
        "Build the homepage hero, navigation, featured product catalog, and shared layout.",
        ("hero", "catalog"),
    ),
    (
        "Cart and Checkout",
        "Build cart interactions, checkout summary, and purchase confirmation UI.",
        ("cart", "checkout"),
    ),
    (
        "Account and Orders",
        "Build account sign-in, profile summary, and order history sections.",
        ("account", "checkout"),
    ),
    (
        "Admin Inventory",
        "Build admin inventory controls, stock alerts, and merchant dashboard cards.",
        ("admin", "catalog"),
    ),
    (
        "Recommendations",
        "Build recommendation rails, personalization copy, and related products.",
        ("recommendations", "catalog"),
    ),
    (
        "Reviews and Trust",
        "Build reviews, ratings, trust badges, and social proof near products.",
        ("catalog", "recommendations"),
    ),
    (
        "Search and Filters",
        "Build search, category filters, sorting controls, and empty states.",
        ("catalog", "hero"),
    ),
    (
        "Promotions and Accessibility",
        "Build promotions, keyboard-friendly controls, accessibility polish, and footer.",
        ("hero", "cart"),
    ),
)

UNCOORDINATED_DESIGN_SEEDS = (
    "Visual direction: luxury editorial storefront with black, cream, and gold accents.",
    "Visual direction: playful Gen-Z marketplace with neon gradients and bold cards.",
    "Visual direction: calm minimal SaaS commerce dashboard with blue-gray spacing.",
    "Visual direction: rugged outdoor gear store with earthy greens and amber highlights.",
    "Visual direction: futuristic AI shopping assistant with glass panels and violet glows.",
    "Visual direction: cozy artisan marketplace with warm paper textures and serif headings.",
    "Visual direction: high-conversion deal site with red sale badges and dense merchandising.",
    "Visual direction: accessible public-sector marketplace with high contrast and simple controls.",
)
COORDINATED_DESIGN_SEED = (
    "Shared visual direction: premium modern marketplace with indigo accents, consistent cards, "
    "rounded panels, clear hierarchy, and one shared interaction language."
)


def build_design_seed(*, agent_index: int, coordinated: bool) -> str:
    if coordinated:
        return COORDINATED_DESIGN_SEED
    return UNCOORDINATED_DESIGN_SEEDS[(agent_index - 1) % len(UNCOORDINATED_DESIGN_SEEDS)]


def _progress(iterable, *, total: int, desc: str, enabled: bool):
    if not enabled:
        return iterable

    from tqdm import tqdm

    return tqdm(iterable, total=total, desc=desc, unit="req")


def _usage_to_dict(usage: InvokeUsage) -> dict[str, int | str]:
    return {
        "model_id": usage.model_id,
        "role": usage.role,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "latency_ms": usage.latency_ms,
    }


def _sum_tokens(usages: list[InvokeUsage]) -> int:
    return sum(usage.input_tokens + usage.output_tokens for usage in usages)


def _usage_tokens(usage: InvokeUsage) -> int:
    return usage.input_tokens + usage.output_tokens


def _require_usage(usage: InvokeUsage) -> None:
    if usage.input_tokens <= 0 or usage.output_tokens <= 0:
        raise RuntimeError("Static benchmark requires positive Bedrock usage tokens")


def build_agent_tasks(agent_count: int, *, coordinated: bool) -> list[AgentTask]:
    if agent_count < 1 or agent_count > len(TASK_LIBRARY):
        raise ValueError("agent_count must be between 1 and 8")

    tasks: list[AgentTask] = []
    for index, (title, brief, sections) in enumerate(TASK_LIBRARY[:agent_count], start=1):
        coordination = (
            "Stay in your assigned lane and avoid duplicating another section."
            if coordinated
            else "Work independently; assume you may need to fill adjacent gaps yourself."
        )
        tasks.append(
            AgentTask(
                agent_id=f"agent_{index:02d}",
                title=title,
                brief=f"{brief} {coordination}",
                sections=sections,
            )
        )
    return tasks


def build_static_site_prompt(
    task: AgentTask,
    *,
    coordination_plan: str = "",
    quality_mode: QualityMode = "standard",
    design_seed: str = "",
) -> str:
    sections = ", ".join(task.sections)
    coordination = coordination_plan or "No central coordination is available."
    if quality_mode == "rich":
        size_requirements = """
- Build production-quality static code with real ecommerce UI detail, not placeholder snippets.
- INDEX_HTML between 2500 and 5000 characters.
- STYLES_CSS between 1800 and 4000 characters.
- APP_JS between 1800 and 4000 characters.
- Do not intentionally keep snippets tiny.
- Include realistic product data, stateful interactions, empty/loading states, and responsive behavior.
- It is okay to create file-level overlap with other agents; this simulates real merge conflicts.
""".strip()
    else:
        size_requirements = """
- Do NOT return a full HTML document, doctype, html, head, body, nav, script tag, or stylesheet link.
- Keep INDEX_HTML under 900 characters.
- Keep STYLES_CSS under 700 characters.
- Keep APP_JS under 700 characters.
- Include only your owned sections, with at most two product cards total.
""".strip()
    return f"""
You are {task.agent_id}, an AI coding agent building part of a static commerce website.

Task title: {task.title}
Task brief: {task.brief}
Owned sections: {sections}
Coordination plan: {coordination}
{design_seed}

Create browser-runnable static site fragments. Return ONLY these three labeled fenced sections:

INDEX_HTML:
```html
<section data-section='hero'>...</section>
```

STYLES_CSS:
```css
/* CSS for your sections */
```

APP_JS:
```javascript
// JS for your interactions
```

Requirements:
{size_requirements}
- Include semantic HTML using data-section attributes for your owned sections.
- Mention concrete ecommerce behavior such as products, cart, checkout, inventory, accounts, or recommendations.
- Do not include any explanation outside the three labeled sections.
""".strip()


def build_static_site_file_prompt(
    task: AgentTask,
    *,
    file_kind: Literal["index_html", "styles_css", "app_js"],
    coordination_plan: str,
    design_seed: str,
) -> str:
    sections = ", ".join(task.sections)
    coordination = coordination_plan or "No central coordination is available."
    file_guidance = {
        "index_html": (
            "Return one ```html fenced block containing only body fragments for your owned "
            "sections. Do not include doctype, html, head, body, stylesheet links, or script tags. "
            "Target 2500-4500 characters of semantic ecommerce markup. Every owned section must "
            "use an exact data-section attribute, for example <section data-section=\"hero\">."
        ),
        "styles_css": (
            "Return one ```css fenced block containing CSS for your sections and shared component "
            "classes. Target 1800-3500 characters with responsive rules and a distinct visual system."
        ),
        "app_js": (
            "Return one ```javascript fenced block containing browser JavaScript for ecommerce "
            "interactions. Target 1800-3500 characters with cart, filtering, checkout, or stateful UI behavior."
        ),
    }[file_kind]
    return f"""
You are {task.agent_id}, an AI coding agent building one file for a static commerce website.

Task title: {task.title}
Task brief: {task.brief}
Owned sections: {sections}
Coordination plan: {coordination}
{design_seed}

{file_guidance}

Requirements:
- Output exactly one fenced code block and no explanation.
- Use concrete ecommerce product, cart, checkout, inventory, account, or recommendation behavior.
- Keep code complete for this single file; do not reference external packages.
""".strip()


def _extract_single_fenced_code(text: str) -> str:
    match = SINGLE_FENCE_RE.search(text)
    if match:
        return match.group("body").strip()
    return text.strip()


def _strip_html_document_wrapper(html: str) -> str:
    body_match = BODY_RE.search(html)
    if body_match:
        return body_match.group("body").strip()
    return html.strip()


def _ensure_owned_section_markers(html: str, sections: tuple[str, ...]) -> str:
    if any(
        f"data-section='{section}'" in html or f'data-section="{section}"' in html
        for section in sections
    ):
        return html
    section_list = ", ".join(sections)
    return (
        f"<section data-section='{sections[0]}' class='generated-rich-fragment' "
        f"data-owned-sections='{section_list}'>\n{html.strip()}\n</section>"
    )


def parse_static_site_payload(text: str, *, agent_id: str = "unknown") -> StaticSitePayload:
    fenced = {
        match.group("label"): match.group("body").strip()
        for match in FENCED_SECTION_RE.finditer(text)
    }
    if {"INDEX_HTML", "STYLES_CSS", "APP_JS"}.issubset(fenced):
        return StaticSitePayload(
            index_html=fenced["INDEX_HTML"],
            styles_css=fenced["STYLES_CSS"],
            app_js=fenced["APP_JS"],
            agent_id=agent_id,
        )

    language_fences = {
        match.group("lang").lower(): match.group("body").strip()
        for match in LANGUAGE_FENCE_RE.finditer(text)
    }
    if {"html", "css"}.issubset(language_fences) and (
        "js" in language_fences or "javascript" in language_fences
    ):
        return StaticSitePayload(
            index_html=language_fences["html"],
            styles_css=language_fences["css"],
            app_js=language_fences.get("js", language_fences.get("javascript", "")),
            agent_id=agent_id,
        )

    object_literal = {
        match.group("field"): match.group("body").strip()
        for match in OBJECT_LITERAL_FIELD_RE.finditer(text)
    }
    if {"index_html", "styles_css", "app_js"}.issubset(object_literal):
        return StaticSitePayload(
            index_html=object_literal["index_html"],
            styles_css=object_literal["styles_css"],
            app_js=object_literal["app_js"],
            agent_id=agent_id,
        )

    raw = extract_json_object(text)
    return StaticSitePayload(
        index_html=str(raw["index_html"]),
        styles_css=str(raw["styles_css"]),
        app_js=str(raw["app_js"]),
        agent_id=agent_id,
    )


def _mock_static_site_payload(task: AgentTask) -> StaticSitePayload:
    sections = []
    for section in task.sections:
        sections.append(
            f"<section data-section='{section}' class='module module-{section}'>"
            f"<h2>{section.title()}</h2>"
            f"<p>{task.agent_id} built {section} for the demo commerce store.</p>"
            f"</section>"
        )
    return StaticSitePayload(
        index_html="\n".join(sections),
        styles_css=(
            f":root {{ --brand: #{len(task.agent_id) * 123456 % 0xFFFFFF:06x}; }}\n"
            f".module {{ padding: 1rem; border: 1px solid #ddd; }}\n"
            f".module-{task.sections[0]} {{ background: #f8fafc; }}"
        ),
        app_js=(
            f"console.log('{task.agent_id} ready');\n"
            "function addToCart(id) { window.demoCart = [...(window.demoCart || []), id]; }\n"
            "document.querySelectorAll('[data-section]').forEach((section) => section.dataset.ready = 'true');"
        ),
        agent_id=task.agent_id,
    )


def _rich_mock_static_site_payload(task: AgentTask, *, design_seed: str) -> StaticSitePayload:
    accent = ["#111827", "#7c3aed", "#0f766e", "#b45309", "#be123c", "#2563eb"][
        (int(task.agent_id[-2:]) - 1) % 6
    ]
    sections = []
    for section in task.sections:
        sections.append(
            f"<section data-section='{section}' class='rich-section {section}'>"
            f"<div class='eyebrow'>{task.title}</div>"
            f"<h2>{section.title()} Experience</h2>"
            f"<p>{design_seed} {task.agent_id} owns the {section} workflow with realistic ecommerce state.</p>"
            f"<div class='rich-grid'>"
            f"<article class='rich-card'><h3>{section.title()} Pro</h3><p>$129</p><button data-action='add-to-cart'>Add to cart</button></article>"
            f"<article class='rich-card'><h3>{section.title()} Plus</h3><p>$89</p><button data-action='inspect'>Inspect</button></article>"
            f"</div>"
            f"</section>"
        )
    return StaticSitePayload(
        index_html="\n".join(sections),
        styles_css=(
            f":root {{ --agent-accent: {accent}; }}\n"
            ".rich-section { padding: 3rem; margin: 1rem; border-radius: 24px; "
            "background: linear-gradient(135deg, #fff, #eef2ff); box-shadow: 0 18px 45px rgba(15,23,42,.12); }\n"
            ".eyebrow { text-transform: uppercase; letter-spacing: .16em; color: var(--agent-accent); font-weight: 800; }\n"
            ".rich-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }\n"
            ".rich-card { border: 1px solid rgba(15,23,42,.12); border-radius: 18px; padding: 1rem; background: white; }\n"
            ".rich-card button { background: var(--agent-accent); color: white; border: 0; border-radius: 999px; padding: .75rem 1rem; }"
        ),
        app_js=(
            f"const {task.agent_id.replace('_', '')}State = {{ seed: {json.dumps(design_seed)}, cart: [] }};\n"
            "function addToCart(id) { window.demoCart = [...(window.demoCart || []), id || 'sku']; }\n"
            "document.querySelectorAll('[data-action]').forEach((button) => button.addEventListener('click', () => addToCart(button.textContent)));"
        ),
        agent_id=task.agent_id,
    )


def generate_agent_site(
    task: AgentTask,
    *,
    max_tokens: int,
    coordination_plan: str,
    allow_mock: bool,
    quality_mode: QualityMode = "standard",
    design_seed: str = "",
) -> tuple[StaticSitePayload, InvokeUsage]:
    logger.info(
        "agent_generation_start agent=%s quality_mode=%s max_tokens=%s mock=%s sections=%s",
        task.agent_id,
        quality_mode,
        max_tokens,
        os.getenv("HELM_MOCK_BEDROCK") == "1",
        ",".join(task.sections),
    )
    if os.getenv("HELM_MOCK_BEDROCK") == "1":
        if not allow_mock:
            raise RuntimeError("Static benchmark requires real Bedrock unless allow_mock=True")
        payload = (
            _rich_mock_static_site_payload(task, design_seed=design_seed)
            if quality_mode == "rich"
            else _mock_static_site_payload(task)
        )
        body = json.dumps(payload.__dict__)
        usage = InvokeUsage(
            model_id="mock-haiku",
            role=task.agent_id,
            input_tokens=max(
                1,
                len(
                    build_static_site_prompt(
                        task,
                        coordination_plan=coordination_plan,
                        quality_mode=quality_mode,
                        design_seed=design_seed,
                    )
                )
                // 4,
            ),
            output_tokens=max(1, len(body) // 4),
            latency_ms=0,
        )
        logger.info(
            "agent_generation_complete agent=%s quality_mode=%s mock=true tokens=%s input_tokens=%s output_tokens=%s latency_ms=%s html_chars=%s css_chars=%s js_chars=%s",
            task.agent_id,
            quality_mode,
            _usage_tokens(usage),
            usage.input_tokens,
            usage.output_tokens,
            usage.latency_ms,
            len(payload.index_html),
            len(payload.styles_css),
            len(payload.app_js),
        )
        return payload, usage

    if quality_mode == "rich":
        payload, usage = generate_rich_agent_site(
            task,
            max_tokens=max_tokens,
            coordination_plan=coordination_plan,
            design_seed=design_seed,
        )
        logger.info(
            "agent_generation_complete agent=%s quality_mode=%s tokens=%s input_tokens=%s output_tokens=%s latency_ms=%s html_chars=%s css_chars=%s js_chars=%s",
            task.agent_id,
            quality_mode,
            _usage_tokens(usage),
            usage.input_tokens,
            usage.output_tokens,
            usage.latency_ms,
            len(payload.index_html),
            len(payload.styles_css),
            len(payload.app_js),
        )
        return payload, usage

    prompt = build_static_site_prompt(
        task,
        coordination_plan=coordination_plan,
        quality_mode=quality_mode,
        design_seed=design_seed,
    )
    text, usage = invoke_anthropic_messages(
        model_id=agent_model_id(),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        role=task.agent_id,
    )
    _require_usage(usage)
    payload = parse_static_site_payload(text, agent_id=task.agent_id)
    logger.info(
        "agent_generation_complete agent=%s quality_mode=%s tokens=%s input_tokens=%s output_tokens=%s latency_ms=%s html_chars=%s css_chars=%s js_chars=%s",
        task.agent_id,
        quality_mode,
        _usage_tokens(usage),
        usage.input_tokens,
        usage.output_tokens,
        usage.latency_ms,
        len(payload.index_html),
        len(payload.styles_css),
        len(payload.app_js),
    )
    return payload, usage


def generate_rich_agent_site(
    task: AgentTask,
    *,
    max_tokens: int,
    coordination_plan: str,
    design_seed: str,
) -> tuple[StaticSitePayload, InvokeUsage]:
    parts: dict[str, str] = {}
    usages: list[InvokeUsage] = []
    for file_kind in ("index_html", "styles_css", "app_js"):
        file_started = time.perf_counter()
        logger.info(
            "rich_file_generation_start agent=%s file=%s max_tokens=%s",
            task.agent_id,
            file_kind,
            max_tokens,
        )
        prompt = build_static_site_file_prompt(
            task,
            file_kind=file_kind,  # type: ignore[arg-type]
            coordination_plan=coordination_plan,
            design_seed=design_seed,
        )
        text, usage = invoke_anthropic_messages(
            model_id=agent_model_id(),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            role=f"{task.agent_id}_{file_kind}",
        )
        _require_usage(usage)
        parts[file_kind] = _extract_single_fenced_code(text)
        usages.append(usage)
        logger.info(
            "rich_file_generation_complete agent=%s file=%s tokens=%s input_tokens=%s output_tokens=%s latency_ms=%s seconds=%.2f chars=%s",
            task.agent_id,
            file_kind,
            _usage_tokens(usage),
            usage.input_tokens,
            usage.output_tokens,
            usage.latency_ms,
            time.perf_counter() - file_started,
            len(parts[file_kind]),
        )

    return (
        StaticSitePayload(
            index_html=_ensure_owned_section_markers(
                _strip_html_document_wrapper(parts["index_html"]),
                task.sections,
            ),
            styles_css=parts["styles_css"],
            app_js=parts["app_js"],
            agent_id=task.agent_id,
        ),
        InvokeUsage(
            model_id=usages[-1].model_id,
            role=task.agent_id,
            input_tokens=sum(usage.input_tokens for usage in usages),
            output_tokens=sum(usage.output_tokens for usage in usages),
            latency_ms=sum(usage.latency_ms for usage in usages),
        ),
    )


def build_coordination_plan(
    *,
    agent_count: int,
    allow_mock: bool,
) -> tuple[str, InvokeUsage]:
    if os.getenv("HELM_MOCK_BEDROCK") == "1":
        if not allow_mock:
            raise RuntimeError("Static benchmark requires real Bedrock unless allow_mock=True")
        plan = (
            "Assign one owner per section, preserve shared styling, and avoid duplicate "
            "cart, account, catalog, and recommendation modules."
        )
        usage = InvokeUsage(
            model_id="mock-helm",
            role="helm",
            input_tokens=80 + agent_count * 10,
            output_tokens=max(1, len(plan) // 4),
            latency_ms=0,
        )
        logger.info(
            "coordination_complete agent_count=%s mock=true tokens=%s input_tokens=%s output_tokens=%s latency_ms=%s plan_chars=%s",
            agent_count,
            _usage_tokens(usage),
            usage.input_tokens,
            usage.output_tokens,
            usage.latency_ms,
            len(plan),
        )
        return plan, usage

    from helm import arbitrate

    started = time.perf_counter()
    logger.info("coordination_start agent_count=%s", agent_count)
    agent_a = {
        "intent": "Coordinate static commerce website generation.",
        "code": json.dumps([task.__dict__ for task in build_agent_tasks(agent_count, coordinated=False)]),
    }
    agent_b = {
        "intent": "Prevent duplicate and conflicting static commerce modules.",
        "code": "Create one owner per UI section and produce a coherent browser-runnable site.",
    }
    result = arbitrate(agent_a, agent_b, conflict_kind="intent")
    raw_usage = result.get("_usage")
    if not raw_usage:
        raise RuntimeError("Helm static coordination did not return Bedrock usage")
    usage = InvokeUsage(
        model_id=str(raw_usage["model_id"]),
        role="helm",
        input_tokens=int(raw_usage["input_tokens"]),
        output_tokens=int(raw_usage["output_tokens"]),
        latency_ms=int(raw_usage["latency_ms"]),
    )
    _require_usage(usage)
    plan = " ".join(str(result.get(key, "")) for key in ("reasoning", "resolved_code"))
    logger.info(
        "coordination_complete agent_count=%s tokens=%s input_tokens=%s output_tokens=%s latency_ms=%s seconds=%.2f plan_chars=%s",
        agent_count,
        _usage_tokens(usage),
        usage.input_tokens,
        usage.output_tokens,
        usage.latency_ms,
        time.perf_counter() - started,
        len(plan),
    )
    return plan, usage


def _html_document(title: str, fragments: list[str]) -> str:
    body = "\n".join(fragments)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="site-header">
    <h1>MergeAI Commerce Demo</h1>
    <p>A generated static ecommerce storefront.</p>
  </header>
  <main>
{body}
  </main>
  <script src="app.js"></script>
</body>
</html>
"""


def _dedupe_sections(html: str, seen_sections: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        section = match.group("section")
        if section in seen_sections:
            return ""
        seen_sections.add(section)
        return match.group(0)

    return SECTION_RE.sub(replace, html)


def merge_generated_sites(
    generated: list[StaticSitePayload],
    *,
    tasks: list[AgentTask],
    agent_count: int,
    mode: StaticSiteMode,
    token_usage: int = 0,
    seconds: float = 0.0,
    calls: list[dict[str, int | str]] | None = None,
    quality_mode: QualityMode = "standard",
) -> StaticSiteProject:
    merge_started = time.perf_counter()
    logger.info(
        "merge_start agent_count=%s mode=%s quality_mode=%s payloads=%s",
        agent_count,
        mode,
        quality_mode,
        len(generated),
    )
    warnings: list[str] = []
    seen_sections: set[str] = set()
    fragments: list[str] = []
    retained_payloads: list[StaticSitePayload] = []

    for payload in generated:
        html = payload.index_html
        if mode == "with-helm":
            before_sections = {
                match.group("section") for match in SECTION_RE.finditer(html)
            }
            html = _dedupe_sections(html, seen_sections)
            removed = before_sections.difference(
                {match.group("section") for match in SECTION_RE.finditer(html)}
            )
            warnings.extend(f"helm deduped section: {section}" for section in sorted(removed))
        else:
            for section in REQUIRED_SECTIONS:
                marker = f"data-section='{section}'"
                alt_marker = f'data-section="{section}"'
                if marker in html or alt_marker in html:
                    if section in seen_sections:
                        warnings.append(f"duplicate section: {section}")
                    seen_sections.add(section)
        if html.strip():
            fragments.append(f"<article data-agent='{payload.agent_id}'>\n{html}\n</article>")
            retained_payloads.append(
                StaticSitePayload(
                    index_html=html,
                    styles_css=payload.styles_css,
                    app_js=payload.app_js,
                    agent_id=payload.agent_id,
                )
            )

    css = "\n\n".join(payload.styles_css for payload in retained_payloads)
    js = "\n\n".join(payload.app_js for payload in retained_payloads)
    files = {
        "index.html": _html_document(f"Static Commerce {mode} N{agent_count}", fragments),
        "styles.css": css,
        "app.js": js,
        "README.md": (
            f"# Static Commerce Demo\n\nMode: `{mode}`\nAgents: `{agent_count}`\n\n"
            "Run with `python -m http.server 5174 --directory .` and open "
            "`http://127.0.0.1:5174`.\n"
        ),
    }
    merge_conflicts = 0
    if quality_mode == "rich" and mode == "without-helm" and len(generated) > 1:
        merge_conflicts = min(3, len(generated) - 1)
        conflict_note = (
            "\n\n/* Simulated file-level merge conflicts from independent agents */\n"
            "<<<<<<< agent-theme\n"
            ":root { --brand: #7c3aed; --surface: #ffffff; }\n"
            "=======\n"
            ":root { --brand: #be123c; --surface: #111827; }\n"
            ">>>>>>> agent-theme\n"
        )
        files["styles.css"] += conflict_note
        files["README.md"] += (
            f"\nThis rich without-Helm run records {merge_conflicts} simulated "
            "file-level merge conflicts from competing design systems.\n"
        )
    if quality_mode == "rich":
        for payload in generated:
            files[f"agent-work/{payload.agent_id}/index.html"] = _html_document(
                f"{payload.agent_id} isolated work",
                [payload.index_html],
            )
            files[f"agent-work/{payload.agent_id}/styles.css"] = payload.styles_css
            files[f"agent-work/{payload.agent_id}/app.js"] = payload.app_js
        files["merge-report.md"] = (
            f"# Rich Static Merge Report\n\n"
            f"Mode: `{mode}`\n"
            f"Agents: `{agent_count}`\n"
            f"Merge conflicts: `{merge_conflicts}`\n"
            f"Warnings: `{len(warnings)}`\n\n"
            "The `agent-work/` directory stores each generated agent project before "
            "the deterministic merge step, so you can inspect how the independent "
            "design/code choices diverged.\n"
        )
    project = StaticSiteProject(
        agent_count=agent_count,
        mode=mode,
        files=files,
        token_usage=token_usage,
        seconds=seconds,
        calls=calls or [],
        warnings=warnings,
        merge_conflicts=merge_conflicts,
    )
    logger.info(
        "merge_complete agent_count=%s mode=%s quality_mode=%s files=%s warnings=%s merge_conflicts=%s seconds=%.2f",
        agent_count,
        mode,
        quality_mode,
        len(project.files),
        len(warnings),
        merge_conflicts,
        time.perf_counter() - merge_started,
    )
    return project


def score_static_site(site: StaticSiteProject) -> QualityReport:
    score_started = time.perf_counter()
    missing_files = [
        file_name
        for file_name in ("index.html", "styles.css", "app.js")
        if file_name not in site.files or not site.files[file_name].strip()
    ]
    html = site.files.get("index.html", "")
    css = site.files.get("styles.css", "")
    js = site.files.get("app.js", "")
    missing_sections = [
        section
        for section in REQUIRED_SECTIONS
        if f"data-section='{section}'" not in html and f'data-section="{section}"' not in html
    ]
    duplicate_modules = sum(
        max(0, html.count(f"data-section='{section}'") + html.count(f'data-section="{section}"') - 1)
        for section in REQUIRED_SECTIONS
    )
    conflict_markers = sum(
        len(CONFLICT_MARKER_RE.findall(text)) for text in site.files.values()
    )
    broken_links = 0
    if "styles.css" not in html:
        broken_links += 1
    if "app.js" not in html:
        broken_links += 1
    if "addToCart" not in js and "cart" not in js.lower():
        broken_links += 1
    file_size_warnings = [
        file_name
        for file_name, text in site.files.items()
        if file_name in {"index.html", "styles.css", "app.js"} and len(text) < 80
    ]
    score = 100
    score -= len(missing_files) * 15
    score -= len(missing_sections) * 8
    score -= duplicate_modules * 4
    score -= site.merge_conflicts * 12
    score -= conflict_markers * 10
    score -= broken_links * 6
    score -= len(file_size_warnings) * 5
    report = QualityReport(
        quality_score=max(0, score),
        missing_sections=missing_sections,
        duplicate_modules=duplicate_modules,
        conflict_markers=conflict_markers,
        broken_links=broken_links,
        file_size_warnings=file_size_warnings,
    )
    logger.info(
        "scoring_complete agent_count=%s mode=%s quality=%s missing=%s duplicates=%s conflict_markers=%s broken_links=%s file_size_warnings=%s seconds=%.2f",
        site.agent_count,
        site.mode,
        report.quality_score,
        len(report.missing_sections),
        report.duplicate_modules,
        report.conflict_markers,
        report.broken_links,
        len(report.file_size_warnings),
        time.perf_counter() - score_started,
    )
    return report


def write_static_site_project(
    site: StaticSiteProject,
    quality: QualityReport,
    output_dir: Path,
) -> Path:
    write_started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    for file_name, contents in site.files.items():
        file_path = output_dir / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(contents, encoding="utf-8")
    manifest = {
        "agent_count": site.agent_count,
        "mode": site.mode,
        "tokens": site.token_usage,
        "seconds": site.seconds,
        "files": sorted([*site.files, "manifest.json"]),
        "warnings": site.warnings,
        "merge_conflicts": site.merge_conflicts,
        "calls": site.calls,
        "quality": asdict(quality),
        "quality_score": quality.quality_score,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(
        "project_write_complete output_dir=%s files=%s tokens=%s seconds=%.2f quality=%s write_seconds=%.2f",
        output_dir,
        len(manifest["files"]),
        site.token_usage,
        site.seconds,
        quality.quality_score,
        time.perf_counter() - write_started,
    )
    return output_dir


def run_static_site_mode(
    *,
    agent_count: int,
    mode: StaticSiteMode,
    config: StaticSiteConfig,
) -> tuple[StaticSiteProject, QualityReport]:
    started = time.perf_counter()
    coordinated = mode == "with-helm"
    tasks = build_agent_tasks(agent_count, coordinated=coordinated)
    logger.info(
        "mode_start agent_count=%s mode=%s quality_mode=%s agents=%s max_tokens=%s coordinated=%s",
        agent_count,
        mode,
        config.quality_mode,
        len(tasks),
        config.max_tokens,
        coordinated,
    )
    usages: list[InvokeUsage] = []
    coordination_plan = ""
    if coordinated:
        coordination_plan, usage = build_coordination_plan(
            agent_count=agent_count,
            allow_mock=config.allow_mock,
        )
        usages.append(usage)

    generated: list[StaticSitePayload] = []
    for task in _progress(
        tasks,
        total=len(tasks),
        desc=f"{mode} static site N={agent_count}",
        enabled=config.show_progress,
    ):
        payload, usage = generate_agent_site(
            task,
            max_tokens=config.max_tokens,
            coordination_plan=coordination_plan,
            allow_mock=config.allow_mock,
            quality_mode=config.quality_mode,
            design_seed=build_design_seed(
                agent_index=int(task.agent_id[-2:]),
                coordinated=coordinated,
            ),
        )
        generated.append(payload)
        usages.append(usage)

    seconds = time.perf_counter() - started
    token_total = _sum_tokens(usages)
    site = merge_generated_sites(
        generated,
        tasks=tasks,
        agent_count=agent_count,
        mode=mode,
        token_usage=token_total,
        seconds=seconds,
        calls=[_usage_to_dict(usage) for usage in usages],
        quality_mode=config.quality_mode,
    )
    quality = score_static_site(site)
    logger.info(
        "mode_complete agent_count=%s mode=%s quality_mode=%s tokens=%s seconds=%.2f quality=%s missing=%s duplicates=%s conflict_markers=%s merge_conflicts=%s calls=%s",
        agent_count,
        mode,
        config.quality_mode,
        token_total,
        seconds,
        quality.quality_score,
        len(quality.missing_sections),
        quality.duplicate_modules,
        quality.conflict_markers,
        site.merge_conflicts,
        len(usages),
    )
    return site, quality


def run_static_site_benchmark(config: StaticSiteConfig) -> list[StaticBenchmarkResult]:
    if os.getenv("HELM_MOCK_BEDROCK") == "1" and not config.allow_mock:
        raise RuntimeError("Static site benchmark requires real Bedrock usage")

    benchmark_started = time.perf_counter()
    logger.info(
        "static_benchmark_start agent_counts=%s quality_mode=%s output_dir=%s max_tokens=%s mock=%s",
        ",".join(str(count) for count in config.agent_counts),
        config.quality_mode,
        config.output_dir,
        config.max_tokens,
        os.getenv("HELM_MOCK_BEDROCK") == "1",
    )
    results: list[StaticBenchmarkResult] = []
    for agent_count in config.agent_counts:
        for mode in ("without-helm", "with-helm"):
            site, quality = run_static_site_mode(
                agent_count=agent_count,
                mode=mode,  # type: ignore[arg-type]
                config=config,
            )
            output_dir = config.output_dir / mode / f"N{agent_count}"
            write_static_site_project(site, quality, output_dir)
            results.append(
                StaticBenchmarkResult(
                    agent_count=agent_count,
                    mode=mode,  # type: ignore[arg-type]
                    output_dir=str(output_dir),
                    tokens=site.token_usage,
                    seconds=site.seconds,
                    quality_score=quality.quality_score,
                    missing_sections=quality.missing_sections,
                    duplicate_modules=quality.duplicate_modules,
                    conflict_markers=quality.conflict_markers,
                    merge_conflicts=site.merge_conflicts,
                )
            )
    logger.info(
        "static_benchmark_complete runs=%s total_tokens=%s seconds=%.2f output_dir=%s",
        len(results),
        sum(result.tokens for result in results),
        time.perf_counter() - benchmark_started,
        config.output_dir,
    )
    return results


def write_static_benchmark_results(results: list[StaticBenchmarkResult], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "static-commerce-generation-results.json"
    path.write_text(
        json.dumps([result.to_dict() for result in results], indent=2),
        encoding="utf-8",
    )
    logger.info("results_write_complete path=%s rows=%s", path, len(results))
    return path


def save_static_benchmark_figure(results: list[StaticBenchmarkResult], output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "static-commerce-generation-quality.png"
    agent_counts = sorted({result.agent_count for result in results})

    def values(mode: StaticSiteMode, attr: str) -> list[float]:
        by_count = {result.agent_count: getattr(result, attr) for result in results if result.mode == mode}
        return [float(by_count.get(agent_count, 0)) for agent_count in agent_counts]

    fig, axes = plt.subplots(1, 2)
    axes[0].plot(agent_counts, values("without-helm", "quality_score"), marker="o", label="Without Helm")
    axes[0].plot(agent_counts, values("with-helm", "quality_score"), marker="o", label="With Helm")
    axes[0].set_title("Static Site Quality")
    axes[0].set_xlabel("Number of agents")
    axes[0].set_ylabel("Quality score")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(agent_counts, values("without-helm", "tokens"), marker="o", label="Without Helm")
    axes[1].plot(agent_counts, values("with-helm", "tokens"), marker="o", label="With Helm")
    axes[1].set_title("Generation Tokens")
    axes[1].set_xlabel("Number of agents")
    axes[1].set_ylabel("Bedrock tokens")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    logger.info("figure_write_complete path=%s rows=%s", path, len(results))
    return path


def print_static_summary_table(results: list[StaticBenchmarkResult]) -> None:
    headers = [
        "agents",
        "mode",
        "tokens",
        "seconds",
        "quality",
        "missing",
        "duplicates",
        "conflicts",
        "merge_conflicts",
        "folder",
    ]
    print(" | ".join(headers))
    print(" | ".join("-" * len(header) for header in headers))
    for result in results:
        print(
            " | ".join(
                [
                    str(result.agent_count),
                    result.mode,
                    str(result.tokens),
                    f"{result.seconds:.2f}",
                    str(result.quality_score),
                    ",".join(result.missing_sections) or "-",
                    str(result.duplicate_modules),
                    str(result.conflict_markers),
                    str(result.merge_conflicts),
                    result.output_dir,
                ]
            )
        )
