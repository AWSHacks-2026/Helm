import { useState } from "react";

import {
  type LiveBenchmarkResult,
  runLiveBenchmark,
} from "../api/liveBenchmark";
import {
  type CompareResult,
  compareMergeScenario,
} from "../api/mergeLab";

const SCENARIO = "merge_conflict";

type LoadingAction = "live" | "compare" | null;

export function BenchmarkProof() {
  const [loading, setLoading] = useState<LoadingAction>(null);
  const [error, setError] = useState<string | null>(null);
  const [liveResult, setLiveResult] = useState<LiveBenchmarkResult | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);

  async function handleRunLiveBenchmark() {
    setLoading("live");
    setError(null);

    try {
      setLiveResult(await runLiveBenchmark(SCENARIO, "scenario"));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setLiveResult(null);
    } finally {
      setLoading(null);
    }
  }

  async function handleRunMergeComparison() {
    setLoading("compare");
    setError(null);

    try {
      setCompareResult(await compareMergeScenario(SCENARIO));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setCompareResult(null);
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="benchmark-proof">
      <header className="screen-header">
        <div>
          <p className="eyebrow">With Overlord vs without Overlord</p>
          <h1>Benchmark Proof</h1>
          <p>
            Run the known merge conflict scenario to compare token usage and merge
            quality against naive baselines.
          </p>
        </div>
      </header>

      {error && <p className="demo-error">{error}</p>}

      <section className="proof-actions" aria-label="Benchmark proof actions">
        <button
          type="button"
          disabled={loading !== null}
          onClick={handleRunLiveBenchmark}
        >
          {loading === "live" ? "Running token benchmark..." : "Run live token benchmark"}
        </button>
        <button
          type="button"
          disabled={loading !== null}
          onClick={handleRunMergeComparison}
        >
          {loading === "compare" ? "Running merge comparison..." : "Run merge comparison"}
        </button>
      </section>

      <section className="proof-grid" aria-label="Benchmark summaries">
        {liveResult && (
          <article className="proof-card">
            <p className="eyebrow">Token benchmark</p>
            <h2>Live token summary</h2>
            <dl className="summary-list">
              <div>
                <dt>Baseline tokens</dt>
                <dd>{liveResult.comparison.baseline_tokens}</dd>
              </div>
              <div>
                <dt>Overlord tokens</dt>
                <dd>{liveResult.comparison.overlord_tokens}</dd>
              </div>
              <div>
                <dt>Savings</dt>
                <dd>{liveResult.comparison.token_savings_pct}%</dd>
              </div>
            </dl>
          </article>
        )}

        {compareResult && (
          <article className="proof-card">
            <p className="eyebrow">Merge quality</p>
            <h2>Quality summary</h2>
            <p>
              Overlord score {compareResult.summary.overlord_score}% vs best naive
              score {compareResult.summary.best_naive_score}%.
            </p>
          </article>
        )}

        <article className="proof-card static-commerce-card">
          <p className="eyebrow">Static commerce artifacts</p>
          <h2>Generated output path</h2>
          <p>
            When the rich static commerce benchmark is run, it writes artifacts under{" "}
            <code>overlord/demo/generated/static-commerce-rich/</code>.
          </p>
          <p className="demo-hint">
            These need a backend manifest route before being presented as live
            frontend results; this card is output guidance, not live frontend
            results.
          </p>
        </article>
      </section>
    </main>
  );
}
