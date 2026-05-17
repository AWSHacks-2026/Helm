import { useEffect, useState } from "react";
import {
  CompareResult,
  compareMergeScenario,
  listMergeScenarios,
  MergeScenarioMeta,
  StrategyResult,
} from "./api/mergeLab";
import {
  LiveBenchmarkResult,
  runLiveBenchmark,
} from "./api/liveBenchmark";

const STRATEGY_LABELS: Record<string, string> = {
  overlord: "Overlord",
  pick_agent_a: "Naive — keep Agent A",
  pick_agent_b: "Naive — keep Agent B",
  dual_edit_markers: "Naive — dual edit (markers)",
};

function scoreClass(score: number, passed: boolean) {
  if (passed) return "score-pass";
  if (score >= 50) return "score-partial";
  return "score-fail";
}

function StrategyCard({ row }: { row: StrategyResult }) {
  return (
    <div className="merge-strategy-card">
      <div className="merge-strategy-header">
        <h4>{STRATEGY_LABELS[row.strategy] ?? row.strategy}</h4>
        <span
          className={`merge-score ${scoreClass(
            row.evaluation.score,
            row.evaluation.passed
          )}`}
        >
          {row.evaluation.score}%{row.evaluation.passed ? " ✓" : ""}
        </span>
      </div>
      <p className="merge-timing">{row.elapsed_ms} ms</p>
      <pre>{row.resolved_code}</pre>
      <details>
        <summary>Checks</summary>
        <ul>
          {Object.entries(row.evaluation.checks).map(([k, v]) => (
            <li key={k}>
              {v ? "✓" : "✗"} {k}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}

export default function MergeLab() {
  const [scenarios, setScenarios] = useState<MergeScenarioMeta[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [compare, setCompare] = useState<CompareResult | null>(null);
  const [live, setLive] = useState<LiveBenchmarkResult | null>(null);
  const [seedMode, setSeedMode] = useState<"scenario" | "haiku">("scenario");

  useEffect(() => {
    listMergeScenarios()
      .then((list) => {
        setScenarios(list);
        if (list.length) setSelected(list[0].name);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : String(err))
      );
  }, []);

  async function runCompare() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    setLive(null);
    try {
      setCompare(await compareMergeScenario(selected));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setCompare(null);
    } finally {
      setLoading(false);
    }
  }

  async function runLive() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    setCompare(null);
    try {
      setLive(await runLiveBenchmark(selected, seedMode));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setLive(null);
    } finally {
      setLoading(false);
    }
  }

  const overlord = compare?.results.find((r) => r.strategy === "overlord");

  return (
    <div className="merge-lab">
      <h2>Merge lab</h2>
      <p className="demo-hint">
        Hardcoded merge conflicts for agent testing. Compare Overlord arbitration
        vs naive single-agent strategies. Set <code>OVERLORD_MOCK_BEDROCK=1</code> on
        the server for deterministic runs.
      </p>
      {error && <p className="demo-error">{error}</p>}

      <div className="merge-toolbar">
        <select
          value={selected ?? ""}
          onChange={(e) => setSelected(e.target.value)}
          disabled={loading}
        >
          {scenarios.map((s) => (
            <option key={s.name} value={s.name}>
              {s.title}
            </option>
          ))}
        </select>
        <button type="button" disabled={loading || !selected} onClick={runCompare}>
          {loading ? "Comparing…" : "Run compare"}
        </button>
        <select
          value={seedMode}
          onChange={(e) => setSeedMode(e.target.value as "scenario" | "haiku")}
          disabled={loading}
          title="Seed mode for live benchmark"
        >
          <option value="scenario">Seed: scenario</option>
          <option value="haiku">Seed: haiku</option>
        </select>
        <button
          type="button"
          className="demo-smoke-btn"
          disabled={loading || !selected}
          onClick={runLive}
        >
          {loading ? "Running…" : "Run live benchmark"}
        </button>
      </div>

      {live && (
        <div
          className={`live-benchmark-summary ${
            live.comparison.overlord_beats_cost ? "pass" : "fail"
          }`}
        >
          <h3>Live benchmark (Haiku vs Overlord)</h3>
          {live.mock_bedrock && (
            <p className="demo-hint">Mock Bedrock — costs are estimated from mock usage.</p>
          )}
          <p>
            Baseline {live.comparison.baseline_cost_display} (
            {live.comparison.baseline_score}%,{" "}
            {live.comparison.baseline_passed ? "passed" : "failed"}) · Overlord{" "}
            {live.comparison.overlord_cost_display} ({live.comparison.overlord_score}%,{" "}
            {live.comparison.overlord_passed ? "passed" : "failed"}) · Saved{" "}
            {live.comparison.cost_savings_pct}% cost
          </p>
          <p className="demo-hint">
            Tokens: {live.comparison.baseline_tokens} → {live.comparison.overlord_tokens}{" "}
            ({live.comparison.token_savings_pct}%) — Sonnet costs more per token; compare USD.
          </p>
          {live.comparison.cost_note && (
            <p className="demo-hint">{live.comparison.cost_note}</p>
          )}
          <p>
            Rounds: baseline {live.baseline.rounds} vs Overlord {live.overlord.rounds}
          </p>
          <details>
            <summary>Baseline final code</summary>
            <pre>{live.baseline.final_code}</pre>
          </details>
          <details>
            <summary>Overlord final code</summary>
            <pre>{live.overlord.final_code}</pre>
          </details>
        </div>
      )}

      {compare && (
        <>
          <div
            className={`merge-summary ${
              compare.summary.overlord_beats_naive ? "pass" : "fail"
            }`}
          >
            <h3>
              {compare.summary.overlord_beats_naive
                ? "Overlord beats best naive baseline"
                : "Overlord did not beat naive baseline"}
            </h3>
            <p>
              Overlord {compare.summary.overlord_score}% (
              {compare.summary.overlord_passed ? "passed" : "failed"}) vs best naive{" "}
              {compare.summary.best_naive_score}% ({compare.summary.best_naive_strategy}
              ) — delta +{compare.summary.score_delta}
            </p>
            <p className="merge-file">
              File: <code>{compare.file_path}</code>
              {compare.mock_bedrock && " · mock Bedrock"}
            </p>
          </div>

          <div className="merge-conflict-grid">
            <div className="merge-panel">
              <h4>Agent A</h4>
              <pre>{compare.agent_a.intent}</pre>
              <pre>{compare.agent_a.code}</pre>
            </div>
            <div className="merge-panel">
              <h4>Agent B</h4>
              <pre>{compare.agent_b.intent}</pre>
              <pre>{compare.agent_b.code}</pre>
            </div>
          </div>

          {overlord && (
            <div className="merge-overlord-block">
              <h4>Overlord resolution</h4>
              <pre>{overlord.reasoning}</pre>
              <p>Tokens saved: {overlord.tokens_saved_estimate ?? "—"}</p>
            </div>
          )}

          <div className="merge-strategies-grid">
            {compare.results.map((row) => (
              <StrategyCard key={row.strategy} row={row} />
            ))}
          </div>

          <details className="merge-mcp-hint">
            <summary>Agent / MCP test hint</summary>
            <pre>
              {JSON.stringify(
                {
                  tool: compare.mcp_hint.tool,
                  session_id: compare.mcp_hint.session_id,
                  file_path: compare.mcp_hint.file_path,
                  agent_a_code: compare.agent_a.code.slice(0, 80) + "…",
                  agent_b_code: compare.agent_b.code.slice(0, 80) + "…",
                },
                null,
                2
              )}
            </pre>
          </details>
        </>
      )}
    </div>
  );
}
