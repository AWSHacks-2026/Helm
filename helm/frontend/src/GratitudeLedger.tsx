import { useCallback, useEffect, useState } from "react";

import { fetchGratitude, type GratitudeLedger as Ledger } from "./api/gratitude";
import {
  GRATITUDE_EMPTY_HINT,
  GRATITUDE_ERROR_FETCH,
  GRATITUDE_ERROR_NO_SESSION,
  GRATITUDE_INTRO,
  GRATITUDE_LOADING,
  GRATITUDE_SESSION_TITLE,
  GRATITUDE_WHY,
  HACKATHON_THEME,
  PRODUCT_NAME,
  ROADMAP_EYEBROW,
  ROADMAP_ITEMS,
} from "./content/gratitudeMission";
import { Illustration } from "./components/Illustration";
import { useConflictStream } from "./hooks/useConflictStream";
import { motionAllowed, useCountUp } from "./hooks/useCountUp";

type Props = {
  sessionId: string;
  onRefresh?: () => void;
};

const METRIC_HINTS: Record<string, string> = {
  Blocked: "Risky write stopped early. Someone keeps their evening.",
  Deduped: "Overlap cut before two agents rebuilt the same file",
  Yielded: "Routed to new work instead of thrashing",
  Tokens: "Model spend you did not burn on rework",
  Haiku: "Fast coordination. Bedrock only when it matters.",
  Sonnet: "One hard merge instead of many agent rounds",
};

export default function GratitudeLedgerPanel({ sessionId, onRefresh }: Props) {
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [newEventKey, setNewEventKey] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!sessionId) {
      setError(GRATITUDE_ERROR_NO_SESSION);
      return;
    }
    setRefreshing(true);
    try {
      setError(null);
      setLedger(await fetchGratitude(sessionId));
      onRefresh?.();
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      setError(`${GRATITUDE_ERROR_FETCH} (${detail})`);
      setLedger(null);
    } finally {
      setRefreshing(false);
    }
  }, [sessionId, onRefresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useConflictStream(
    sessionId,
    useCallback(() => {
      setNewEventKey(`ws-${Date.now()}`);
      refresh();
    }, [refresh]),
  );

  useEffect(() => {
    const onLedgerUpdated = () => {
      refresh();
    };
    window.addEventListener("helm-ledger-updated", onLedgerUpdated);
    return () => window.removeEventListener("helm-ledger-updated", onLedgerUpdated);
  }, [refresh]);

  return (
    <main className="gratitude-page">
      <header className="screen-header">
        <div>
          <p className="eyebrow">
            {HACKATHON_THEME} · {PRODUCT_NAME}
          </p>
          <h1>Gratitude</h1>
          <p className="gratitude-lede">{GRATITUDE_INTRO}</p>
          <p className="gratitude-why">{GRATITUDE_WHY}</p>
        </div>
      </header>


      <section className="gratitude-session" aria-labelledby="gratitude-session-title">
        <header className="gratitude-session-header">
          <div>
            <p className="eyebrow">Session ledger</p>
            <h2 id="gratitude-session-title">{GRATITUDE_SESSION_TITLE}</h2>
            <p className="gratitude-session-meta">
              Session <code>{sessionId || "—"}</code>
              {ledger ? " · updates as coordination pays back" : " · loading…"}
            </p>
          </div>
          <button type="button" onClick={refresh} disabled={!sessionId || refreshing}>
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </header>

        {error && <p className="demo-error">{error}</p>}

        {ledger ? (
          <>
            <div className="gratitude-cards">
              <Metric
                label="Blocked"
                value={ledger.guardrails_blocked}
                hint={METRIC_HINTS.Blocked}
              />
              <Metric
                label="Deduped"
                value={ledger.duplicates_avoided}
                hint={METRIC_HINTS.Deduped}
              />
              <Metric
                label="Yielded"
                value={ledger.agents_yielded}
                hint={METRIC_HINTS.Yielded}
              />
              <Metric
                label="Tokens"
                value={ledger.tokens_saved_display}
                hint={METRIC_HINTS.Tokens}
                highlight
              />
              <Metric label="Haiku" value={ledger.haiku_calls} hint={METRIC_HINTS.Haiku} />
              <Metric
                label="Sonnet"
                value={ledger.sonnet_calls}
                hint={METRIC_HINTS.Sonnet}
              />
            </div>

            {ledger.timeline.length > 0 ? (
              <ol className="gratitude-timeline">
                {ledger.timeline.map((item, index) => {
                  const key = `${item.at ?? index}-${item.message}`;
                  return (
                    <li
                      key={key}
                      className={key === newEventKey ? "ledger-row--new" : undefined}
                    >
                      <span className="gratitude-kind">{item.kind}</span>
                      <p>{item.message}</p>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <GratitudeLedgerEmpty />
            )}
          </>
        ) : (
          !error && <p className="gratitude-empty">{GRATITUDE_LOADING}</p>
        )}
      </section>

      <section className="gratitude-roadmap" aria-labelledby="gratitude-roadmap-title">
        <p className="eyebrow">{ROADMAP_EYEBROW}</p>
        <h2 id="gratitude-roadmap-title">What&apos;s next</h2>
        <ul className="gratitude-roadmap-list">
          {ROADMAP_ITEMS.map((item) => (
            <li key={item.id}>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

export function GratitudeLedgerEmpty() {
  return (
    <div className="gratitude-empty">
      <Illustration
        name="empty-ledger"
        alt="Tokens and time returning to the session ledger"
        className="gratitude-empty-art"
      />
      <p>{GRATITUDE_EMPTY_HINT}</p>
    </div>
  );
}

function Metric({
  label,
  value,
  hint,
  highlight = false,
}: {
  label: string;
  value: string | number;
  hint: string;
  highlight?: boolean;
}) {
  const isNumeric = typeof value === "number";
  const animated = useCountUp(isNumeric ? value : 0, {
    enabled: isNumeric && motionAllowed(),
  });
  const display = isNumeric ? animated : value;

  return (
    <article className={`gratitude-card ${highlight ? "gratitude-card-highlight" : ""}`}>
      <span className="gratitude-metric-label">{label}</span>
      <strong>{display}</strong>
      <small>{hint}</small>
    </article>
  );
}
