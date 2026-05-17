import { useState } from "react";
import {
  DemoResolveResult,
  GuardrailDemoResult,
  listDemoScenarios,
  runDemoScenario,
  runDemoSmoke,
  SmokeResult,
} from "./api/demo";

function isGuardrailResult(
  result: DemoResolveResult | GuardrailDemoResult
): result is GuardrailDemoResult {
  return "preflight" in result;
}

export default function DemoLab() {
  const scenarios = listDemoScenarios();
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<
    DemoResolveResult | GuardrailDemoResult | null
  >(null);
  const [smoke, setSmoke] = useState<SmokeResult | null>(null);

  async function run(name: string) {
    setLoading(name);
    setError(null);
    setSmoke(null);
    try {
      setResult(await runDemoScenario(name));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setResult(null);
    } finally {
      setLoading(null);
    }
  }

  async function runAll() {
    setLoading("smoke");
    setError(null);
    setResult(null);
    try {
      setSmoke(await runDemoSmoke());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSmoke(null);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="demo-lab">
      <h2>Demo lab</h2>
      <p className="demo-hint">
        Runs hardcoded PRD scenarios against the Helm API (mock Bedrock when
        enabled on the server).
      </p>
      {error && <p className="demo-error">{error}</p>}

      <div className="demo-actions">
        {scenarios.map((s) => (
          <button
            key={s.name}
            type="button"
            disabled={loading !== null}
            onClick={() => run(s.name)}
          >
            {loading === s.name ? "Running…" : s.title}
          </button>
        ))}
        <button
          type="button"
          className="demo-smoke-btn"
          disabled={loading !== null}
          onClick={runAll}
        >
          {loading === "smoke" ? "Running smoke…" : "Run all (smoke)"}
        </button>
      </div>

      {smoke && (
        <div className={`demo-smoke ${smoke.all_passed ? "pass" : "fail"}`}>
          <h3>Smoke: {smoke.all_passed ? "PASSED" : "FAILED"}</h3>
          <ul>
            {smoke.checks.map((c) => (
              <li key={c.scenario}>
                {c.passed ? "✓" : "✗"} {c.scenario} — {c.endpoint}
                {c.detail ? ` (${c.detail})` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result && (
        <div className="demo-result">
          {isGuardrailResult(result) ? (
            <>
              <h3>Guardrail demo</h3>
              <p>
                Preflight:{" "}
                <strong>{result.preflight.allowed ? "allowed" : "blocked"}</strong>
                {result.preflight.rule ? ` (${result.preflight.rule})` : ""}
              </p>
              <p>Executed: {String(result.executed)}</p>
              {result.resolution && (
                <>
                  <h4>Resolution</h4>
                  <pre>{result.resolution.reasoning}</pre>
                  <pre>{result.resolution.resolved_code}</pre>
                </>
              )}
            </>
          ) : (
            <>
              <h3>{result.resolution.conflict_type}</h3>
              <h4>Agent A</h4>
              <pre>{result.agent_a.intent}</pre>
              <pre>{result.agent_a.code}</pre>
              <h4>Agent B</h4>
              <pre>{result.agent_b.intent}</pre>
              <pre>{result.agent_b.code}</pre>
              <h4>Resolution</h4>
              <pre>{result.resolution.reasoning}</pre>
              <pre>{result.resolution.resolved_code}</pre>
              <p>Tokens saved: {result.resolution.tokens_saved_estimate}</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
