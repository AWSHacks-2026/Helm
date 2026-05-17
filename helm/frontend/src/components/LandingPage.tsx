interface LandingPageProps {
  sessionId: string;
  onSessionIdChange: (sessionId: string) => void;
  onStartReplay: () => void;
  onOpenLiveSession: () => void;
}

export function LandingPage({
  sessionId,
  onSessionIdChange,
  onStartReplay,
  onOpenLiveSession,
}: LandingPageProps) {
  return (
    <main className="landing-page">
      <section className="hero-panel" aria-labelledby="landing-title">
        <p className="eyebrow">Helm Control Tower</p>
        <h1 id="landing-title">Coordinate an AI agent fleet without losing the plot.</h1>
        <p>
          Watch Helm catch merge conflicts, enforce guardrails, and deduplicate
          overlapping work before it turns into review debt.
        </p>
      </section>

      <section className="landing-actions" aria-label="Start control tower">
        <article className="landing-card">
          <p className="eyebrow">Replay mode</p>
          <h2>Watch Demo</h2>
          <p>
            Step through the canned incident timeline and see how Helm redirects
            agents in real time.
          </p>
          <button type="button" onClick={onStartReplay}>
            Watch Demo
          </button>
        </article>

        <article className="landing-card">
          <p className="eyebrow">Live mode</p>
          <h2>Open Live Session</h2>
          <p>
            Connect to a team session and monitor the current fleet state from the
            dashboard.
          </p>
          <label>
            Session ID
            <input
              value={sessionId}
              onChange={(event) => onSessionIdChange(event.target.value)}
              placeholder="mergeai-hackathon-demo"
            />
          </label>
          <button type="button" onClick={onOpenLiveSession}>
            Open Live Session
          </button>
        </article>
      </section>

      <section className="proof-strip" aria-label="Helm proof points">
        <div>
          <strong>Merge conflicts</strong>
          <span>Detected before review.</span>
        </div>
        <div>
          <strong>Guardrails</strong>
          <span>Blocked before risky code ships.</span>
        </div>
        <div>
          <strong>Dedup</strong>
          <span>Agents reassigned away from duplicate work.</span>
        </div>
      </section>
    </main>
  );
}
