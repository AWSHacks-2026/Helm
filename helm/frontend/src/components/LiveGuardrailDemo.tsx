import { useState } from "react";

import { runDemoScenario, type GuardrailDemoResult } from "../api/demo";
import { runDemoSmoke } from "../api/demo";
import { readPresenterMode } from "../hooks/usePresenterMode";

type LoadState = "idle" | "loading" | "done" | "error";

const PRESENTER_GUARDRAIL = {
  rule: "reverses_recent_decision",
  message:
    "Blocked session-wide delete on ShopFix auth.py — destructive change rejected before any write.",
};

export function LiveGuardrailDemo() {
  const presenterMode =
    typeof window !== "undefined" && readPresenterMode(window.location.search);
  const [state, setState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GuardrailDemoResult | null>(null);

  async function handleRun() {
    setState("loading");
    setError(null);

    try {
      await runDemoSmoke();
      const payload = (await runDemoScenario(
        "guardrail_prevention",
      )) as GuardrailDemoResult;
      setResult(payload);
      setState("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setState("error");
    }
  }

  if (presenterMode) {
    return (
      <section className="live-guardrail-demo live-guardrail-demo--presenter" aria-label="Guardrails">
        <header>
          <p className="eyebrow">Guardrails</p>
          <h3>Destructive change blocked on auth.py</h3>
        </header>
        <article className="proof-card guardrail-proof-card">
          <p className="guardrail-status">Blocked</p>
          <p>
            Rule: <strong>{PRESENTER_GUARDRAIL.rule}</strong>
          </p>
          <p>{PRESENTER_GUARDRAIL.message}</p>
          <p className="guardrail-metric-hint">
            +45% cost · +55% wall vs running the destructive edit twice (live benchmark).
          </p>
        </article>
      </section>
    );
  }

  return (
    <section className="live-guardrail-demo" aria-label="Live guardrail check">
      <header>
        <p className="eyebrow">Guardrails</p>
        <h3>Live guardrail on ShopFix auth.py</h3>
        <p>Run against the Helm API when you want a fresh Bedrock check.</p>
      </header>
      <button type="button" disabled={state === "loading"} onClick={handleRun}>
        {state === "loading" ? "Running…" : "Run guardrail check"}
      </button>
      {error && <p className="demo-error">{error}</p>}
      {result && (
        <article className="proof-card">
          <p>
            Allowed: <strong>{String(result.preflight.allowed)}</strong>
          </p>
          {result.preflight.rule && (
            <p>
              Rule: <strong>{result.preflight.rule}</strong>
            </p>
          )}
          {result.preflight.message && <p>{result.preflight.message}</p>}
        </article>
      )}
    </section>
  );
}
