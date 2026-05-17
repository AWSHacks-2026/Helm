import { useEffect, useState } from "react";

import { runDemoSmoke, type SmokeResult } from "../api/demo";

type CheckState = "idle" | "loading" | "ready" | "error";

export function SetupChecker() {
  const [state, setState] = useState<CheckState>("idle");
  const [result, setResult] = useState<SmokeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState("loading");

    runDemoSmoke()
      .then((payload) => {
        if (cancelled) return;
        setResult(payload);
        setState(payload.all_passed ? "ready" : "error");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="setup-checker" aria-label="Helm API pre-flight">
      <p className="eyebrow">Pre-flight</p>
      {state === "loading" && <p>Checking Helm API on port 8000…</p>}
      {state === "error" && error && (
        <div className="setup-checker-error">
          <p>
            <strong>Helm API unreachable.</strong> {error}
          </p>
          <p className="setup-hint">
            The Gratitude ledger needs the API — start Helm so the demo can show time
            returned, not just replay animation.
          </p>
          <p className="setup-hint">
            Start:{" "}
            <code>
              cd helm && source .venv/bin/activate && cd backend && uvicorn main:app
              --reload --port 8000
            </code>
          </p>
        </div>
      )}
      {result && Array.isArray(result.checks) && (
        <ul className="setup-check-list">
          {result.checks.map((check) => (
            <li key={check.endpoint} className={check.passed ? "pass" : "fail"}>
              <span>{check.passed ? "✓" : "✗"}</span>
              <span>{check.scenario}</span>
              <small>{check.detail}</small>
            </li>
          ))}
        </ul>
      )}
      {result && (
        <p className="setup-bedrock-mode">
          Bedrock mode: <strong>{result.mock_bedrock ? "mock" : "live AWS"}</strong>
        </p>
      )}
    </section>
  );
}
