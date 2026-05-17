import json
from pathlib import Path

from agents.static_site_benchmark import (
    DEFAULT_RICH_STATIC_OUTPUT_DIR,
    STATIC_AGENT_COUNTS,
    AgentTask,
    StaticSiteConfig,
    build_agent_tasks,
    build_design_seed,
    build_static_site_prompt,
    generate_agent_site,
    merge_generated_sites,
    parse_static_site_payload,
    run_static_site_benchmark,
    score_static_site,
    write_static_site_project,
)


def test_static_benchmark_defaults_are_small():
    config = StaticSiteConfig()

    assert STATIC_AGENT_COUNTS == (2, 4, 8)
    assert config.agent_counts == STATIC_AGENT_COUNTS
    assert config.max_tokens == 2000
    assert config.show_progress is True
    assert config.quality_mode == "standard"


def test_rich_static_config_uses_separate_folder_and_budget():
    config = StaticSiteConfig.for_quality_mode("rich")

    assert config.output_dir == DEFAULT_RICH_STATIC_OUTPUT_DIR
    assert config.max_tokens == 8000
    assert config.quality_mode == "rich"


def test_design_seeds_make_agents_visually_distinct():
    seed_one = build_design_seed(agent_index=1, coordinated=False)
    seed_two = build_design_seed(agent_index=2, coordinated=False)
    coordinated = build_design_seed(agent_index=2, coordinated=True)

    assert seed_one != seed_two
    assert "visual direction" in seed_one.lower()
    assert "shared visual direction" in coordinated.lower()


def test_build_agent_tasks_scales_to_eight_agents():
    tasks = build_agent_tasks(8, coordinated=False)

    assert len(tasks) == 8
    assert tasks[0].agent_id == "agent_01"
    assert "homepage" in tasks[0].brief.lower()
    assert "accessibility" in tasks[-1].brief.lower()


def test_build_static_site_prompt_requests_json_files():
    task = AgentTask(
        agent_id="agent_01",
        title="Homepage",
        brief="Build the homepage and product catalog.",
        sections=("hero", "catalog"),
    )

    prompt = build_static_site_prompt(task, coordination_plan="Own hero and catalog.")

    assert "static commerce website" in prompt
    assert "INDEX_HTML" in prompt
    assert "STYLES_CSS" in prompt
    assert "APP_JS" in prompt
    assert "Do NOT return a full HTML document" in prompt
    assert "Keep INDEX_HTML under 900 characters" in prompt
    assert "Own hero and catalog." in prompt


def test_build_static_site_prompt_rich_mode_requests_larger_real_app():
    task = AgentTask(
        agent_id="agent_01",
        title="Homepage",
        brief="Build the homepage and product catalog.",
        sections=("hero", "catalog"),
    )

    prompt = build_static_site_prompt(
        task,
        coordination_plan="Use the shared premium marketplace design system.",
        quality_mode="rich",
        design_seed="Visual direction: luxury editorial storefront.",
    )

    assert "Visual direction: luxury editorial storefront." in prompt
    assert "Build production-quality static code" in prompt
    assert "INDEX_HTML between 2500 and 5000 characters" in prompt
    assert "Do not intentionally keep snippets tiny" in prompt


def test_parse_static_site_payload_extracts_model_json():
    payload = parse_static_site_payload(
        """
        ```json
        {
          "index_html": "<main data-section='hero'>Hero</main>",
          "styles_css": ".hero { color: blue; }",
          "app_js": "console.log('cart');"
        }
        ```
        """
    )

    assert payload.index_html.startswith("<main")
    assert "blue" in payload.styles_css
    assert "cart" in payload.app_js


def test_parse_static_site_payload_extracts_fenced_sections():
    payload = parse_static_site_payload(
        """
        INDEX_HTML:
        ```html
        <section data-section="hero">
          <button aria-label="Add item">Add</button>
        </section>
        ```

        STYLES_CSS:
        ```css
        .hero {
          color: blue;
        }
        ```

        APP_JS:
        ```javascript
        function addToCart(id) {
          window.demoCart = [...(window.demoCart || []), id];
        }
        ```
        """
    )

    assert 'data-section="hero"' in payload.index_html
    assert "color: blue" in payload.styles_css
    assert "addToCart" in payload.app_js


def test_parse_static_site_payload_extracts_unlabeled_language_fences():
    payload = parse_static_site_payload(
        """
        ```html
        <section data-section="catalog">Catalog</section>
        ```

        ```css
        .catalog { display: grid; }
        ```

        ```js
        function addToCart(id) { return id; }
        ```
        """
    )

    assert 'data-section="catalog"' in payload.index_html
    assert "display: grid" in payload.styles_css
    assert "addToCart" in payload.app_js


def test_parse_static_site_payload_extracts_object_literal_fences():
    payload = parse_static_site_payload(
        """
        {
          index_html: `<section data-section="cart">
            <button>Add to cart</button>
          </section>`,
          styles_css: `.cart {
            border: 1px solid #ddd;
          }`,
          app_js: `function addToCart(id) {
            window.demoCart = [...(window.demoCart || []), id];
          }`
        }
        """
    )

    assert 'data-section="cart"' in payload.index_html
    assert "border" in payload.styles_css
    assert "demoCart" in payload.app_js


def test_rich_generation_uses_separate_file_calls(monkeypatch):
    calls = []

    def fake_invoke(*, model_id, messages, max_tokens, role):
        calls.append({"role": role, "prompt": messages[0]["content"]})
        if role.endswith("index_html"):
            return (
                "```html\n<section data-section='hero'>Hero</section><section data-section='catalog'>Catalog</section>\n```",
                type(
                    "Usage",
                    (),
                    {
                        "model_id": model_id,
                        "role": role,
                        "input_tokens": 10,
                        "output_tokens": 20,
                        "latency_ms": 1,
                    },
                )(),
            )
        if role.endswith("styles_css"):
            return (
                "```css\n.hero { color: blue; }\n.catalog { display: grid; }\n```",
                type(
                    "Usage",
                    (),
                    {
                        "model_id": model_id,
                        "role": role,
                        "input_tokens": 11,
                        "output_tokens": 21,
                        "latency_ms": 1,
                    },
                )(),
            )
        return (
            "```javascript\nfunction addToCart(id) { window.demoCart = [id]; }\n```",
            type(
                "Usage",
                (),
                {
                    "model_id": model_id,
                    "role": role,
                    "input_tokens": 12,
                    "output_tokens": 22,
                    "latency_ms": 1,
                },
            )(),
        )

    monkeypatch.setattr(
        "agents.static_site_benchmark.invoke_anthropic_messages",
        fake_invoke,
    )
    monkeypatch.delenv("OVERLORD_MOCK_BEDROCK", raising=False)

    payload, usage = generate_agent_site(
        build_agent_tasks(2, coordinated=False)[0],
        max_tokens=8000,
        coordination_plan="",
        allow_mock=False,
        quality_mode="rich",
        design_seed="Visual direction: test.",
    )

    assert [call["role"] for call in calls] == [
        "agent_01_index_html",
        "agent_01_styles_css",
        "agent_01_app_js",
    ]
    assert "Hero" in payload.index_html
    assert "data-section='hero'" in payload.index_html
    assert "color: blue" in payload.styles_css
    assert "addToCart" in payload.app_js
    assert usage.input_tokens == 33
    assert usage.output_tokens == 63


def test_merge_and_score_static_site_detects_sections_and_duplicates():
    tasks = build_agent_tasks(4, coordinated=False)
    generated = [
        parse_static_site_payload(
            json.dumps(
                {
                    "index_html": (
                        "<section data-section='hero'>Hero</section>"
                        "<section data-section='catalog'>Catalog</section>"
                        "<section data-section='cart'>Cart</section>"
                    ),
                    "styles_css": ":root { --brand: blue; }",
                    "app_js": "function addToCart() {}",
                }
            ),
            agent_id="agent_01",
        ),
        parse_static_site_payload(
            json.dumps(
                {
                    "index_html": (
                        "<section data-section='catalog'>Duplicate catalog</section>"
                        "<section data-section='checkout'>Checkout</section>"
                    ),
                    "styles_css": ":root { --brand: green; }",
                    "app_js": "function checkout() {}",
                }
            ),
            agent_id="agent_02",
        ),
    ]

    site = merge_generated_sites(
        generated,
        tasks=tasks,
        agent_count=4,
        mode="without-overlord",
    )
    score = score_static_site(site)

    assert "index.html" in site.files
    assert score.duplicate_modules >= 1
    assert "account" in score.missing_sections
    assert score.quality_score < 100


def test_write_static_site_project_creates_viewable_files(tmp_path):
    tasks = build_agent_tasks(2, coordinated=True)
    generated = [
        parse_static_site_payload(
            json.dumps(
                {
                    "index_html": (
                        "<section data-section='hero'>Hero</section>"
                        "<section data-section='catalog'>Catalog</section>"
                        "<section data-section='cart'>Cart</section>"
                        "<section data-section='checkout'>Checkout</section>"
                        "<section data-section='account'>Account</section>"
                        "<section data-section='admin'>Admin</section>"
                        "<section data-section='recommendations'>Recommendations</section>"
                    ),
                    "styles_css": "body { font-family: sans-serif; }",
                    "app_js": "document.body.dataset.ready = 'true'; addToCart = () => {};",
                }
            ),
            agent_id="agent_01",
        )
    ]
    site = merge_generated_sites(
        generated,
        tasks=tasks,
        agent_count=2,
        mode="with-overlord",
    )
    score = score_static_site(site)

    path = write_static_site_project(site, score, tmp_path)

    assert (path / "index.html").exists()
    assert (path / "styles.css").exists()
    assert (path / "app.js").exists()
    assert (path / "manifest.json").exists()
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    assert "quality_score" in manifest
    assert "manifest.json" in manifest["files"]


def test_score_ignores_css_separator_comments_as_conflicts():
    tasks = build_agent_tasks(2, coordinated=True)
    site = merge_generated_sites(
        [
            parse_static_site_payload(
                json.dumps(
                    {
                        "index_html": (
                            "<section data-section='hero'>Hero</section>"
                            "<section data-section='catalog'>Catalog</section>"
                            "<section data-section='cart'>Cart</section>"
                            "<section data-section='checkout'>Checkout</section>"
                        ),
                        "styles_css": "/* ======= SECTION ======= */\n.hero { color: blue; }",
                        "app_js": "function addToCart(id) { return id; }",
                    }
                ),
                agent_id="agent_01",
            )
        ],
        tasks=tasks,
        agent_count=2,
        mode="with-overlord",
    )

    score = score_static_site(site)

    assert score.conflict_markers == 0


def test_run_static_site_benchmark_mock_writes_all_agent_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("OVERLORD_MOCK_BEDROCK", "1")

    results = run_static_site_benchmark(
        StaticSiteConfig(
            output_dir=tmp_path,
            allow_mock=True,
            show_progress=False,
        )
    )

    assert {(result.agent_count, result.mode) for result in results} == {
        (2, "without-overlord"),
        (2, "with-overlord"),
        (4, "without-overlord"),
        (4, "with-overlord"),
        (8, "without-overlord"),
        (8, "with-overlord"),
    }
    assert (tmp_path / "with-overlord" / "N8" / "index.html").exists()
    assert (tmp_path / "without-overlord" / "N8" / "index.html").exists()
    n8_without = next(
        result
        for result in results
        if result.agent_count == 8 and result.mode == "without-overlord"
    )
    n8_with = next(
        result
        for result in results
        if result.agent_count == 8 and result.mode == "with-overlord"
    )
    assert n8_with.duplicate_modules < n8_without.duplicate_modules
    assert n8_with.quality_score > n8_without.quality_score
    with_html = (tmp_path / "with-overlord" / "N8" / "index.html").read_text(
        encoding="utf-8"
    )
    assert 'class="site-header"' in with_html
    assert 'data-section="hero"' not in with_html


def test_rich_mock_generation_records_file_conflict_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("OVERLORD_MOCK_BEDROCK", "1")

    results = run_static_site_benchmark(
        StaticSiteConfig.for_quality_mode(
            "rich",
            output_dir=tmp_path,
            agent_counts=(4,),
            allow_mock=True,
            show_progress=False,
        )
    )

    without = next(result for result in results if result.mode == "without-overlord")
    with_overlord = next(result for result in results if result.mode == "with-overlord")
    manifest = json.loads(
        (tmp_path / "without-overlord" / "N4" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert without.conflict_markers > 0
    assert with_overlord.conflict_markers == 0
    assert without.quality_score < with_overlord.quality_score
    assert manifest["merge_conflicts"] >= 1
    assert (tmp_path / "without-overlord" / "N4" / "agent-work").exists()


def test_static_benchmark_logs_useful_timing_and_token_events(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("OVERLORD_MOCK_BEDROCK", "1")

    with caplog.at_level("INFO", logger="agents.static_site_benchmark"):
        run_static_site_benchmark(
            StaticSiteConfig(
                output_dir=tmp_path,
                agent_counts=(2,),
                allow_mock=True,
                show_progress=False,
            )
        )

    messages = [record.getMessage() for record in caplog.records]

    assert any("static_benchmark_start" in message for message in messages)
    assert any("mode_start" in message for message in messages)
    assert any("agent_generation_complete" in message for message in messages)
    assert any("mode_complete" in message for message in messages)
    assert any("tokens=" in message for message in messages)
    assert any("seconds=" in message for message in messages)


def test_static_site_generation_script_exists():
    script = Path("overlord/scripts/benchmark_static_site_generation.py")

    assert script.exists()
    assert "run_static_site_benchmark" in script.read_text(encoding="utf-8")
