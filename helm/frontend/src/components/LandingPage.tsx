import { AwsArchitectureStrip } from "./AwsArchitectureStrip";
import { SetupChecker } from "./SetupChecker";
import {
  GRATITUDE_PITCH,
  HACKATHON_HOOK,
  HACKATHON_THEME,
  PRODUCT_NAME,
  TECH_NAME,
} from "../content/gratitudeMission";
import { readPresenterMode } from "../hooks/usePresenterMode";

const SHOPFIX_URL = import.meta.env.VITE_SHOPFIX_URL ?? "http://127.0.0.1:8001";

interface LandingPageProps {
  sessionId: string;
  onSessionIdChange: (sessionId: string) => void;
  onStartReplay: () => void;
  onStartJudgeDemo: () => void;
}

export function LandingPage({
  sessionId,
  onSessionIdChange,
  onStartReplay,
  onStartJudgeDemo,
}: LandingPageProps) {
  const presenterMode =
    typeof window !== "undefined" && readPresenterMode(window.location.search);

  return (
    <main className={`landing-page ${presenterMode ? "landing-page--presenter" : ""}`}>
      <section className="hero-panel" aria-labelledby="landing-title">
        <p className="eyebrow">
          {HACKATHON_THEME} · {PRODUCT_NAME} · {TECH_NAME} Control Tower
        </p>
        <h1 id="landing-title">
          {presenterMode
            ? "Give engineers their hours back."
            : "Coordinate agent fleets — and show what you gave back."}
        </h1>
        <p>{HACKATHON_HOOK}</p>
        <p className="landing-hero-proof">{GRATITUDE_PITCH}</p>
        {!presenterMode && (
          <p className="landing-hero-link">
            <a href="?view=gratitude">Session ledger (Gratitude) →</a>
          </p>
        )}
      </section>

      <AwsArchitectureStrip />

      {!presenterMode && <SetupChecker />}

      <section className="landing-actions" aria-label="Start control tower">
        <article className="landing-card landing-card-primary">
          <p className="eyebrow">{presenterMode ? "Presentation" : "Guided tour"}</p>
          <h2>{presenterMode ? "Begin presentation" : "Start guided demo"}</h2>
          <p>
            {presenterMode
              ? "Replay → Incidents → Gratitude ledger → Results charts."
              : "Control Tower replay, incidents, Gratitude ledger, and benchmark proof."}
          </p>
          <button type="button" className="primary" onClick={onStartJudgeDemo}>
            {presenterMode ? "Begin presentation" : "Start guided demo"}
          </button>
        </article>

        {!presenterMode && (
          <article className="landing-card">
            <p className="eyebrow">Replay only</p>
            <h2>Watch replay</h2>
            <p>Skip the walkthrough — pick a scenario on the Control Tower.</p>
            <label>
              Session ID
              <input
                value={sessionId}
                onChange={(event) => onSessionIdChange(event.target.value)}
                aria-label="Session ID for Gratitude ledger"
              />
            </label>
            <button type="button" onClick={onStartReplay}>
              Watch replay
            </button>
          </article>
        )}
      </section>

      {!presenterMode && (
        <section className="proof-strip" aria-label="Helm capabilities">
          <div>
            <strong>Merge conflicts</strong>
            <span>Sonnet arbitration on shared files.</span>
          </div>
          <div>
            <strong>Guardrails</strong>
            <span>Destructive edits blocked before write.</span>
          </div>
          <div>
            <strong>Dedup</strong>
            <span>Overlapping agents reassigned.</span>
          </div>
        </section>
      )}

      <p className="landing-shopfix-link">
        ShopFix storefront{" "}
        <a href={SHOPFIX_URL} target="_blank" rel="noreferrer">
          {SHOPFIX_URL}
        </a>
      </p>
    </main>
  );
}
