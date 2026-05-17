import { useCallback, useEffect, useState } from "react";
import { fetchGratitude, GratitudeLedger as Ledger } from "./api/gratitude";
import { useConflictStream } from "./hooks/useConflictStream";

type Props = {
  sessionId: string;
  onRefresh?: () => void;
};

export default function GratitudeLedgerPanel({ sessionId, onRefresh }: Props) {
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      setError(null);
      setLedger(await fetchGratitude(sessionId));
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [sessionId, onRefresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useConflictStream(
    sessionId,
    useCallback(() => {
      refresh();
    }, [refresh])
  );

  if (!ledger) {
    return (
      <section className="gratitude-panel">
        <h2>Gratitude Ledger</h2>
        {error && <p style={{ color: "#f88" }}>{error}</p>}
      </section>
    );
  }

  return (
    <section className="gratitude-panel">
      <h2>Gratitude Ledger</h2>
      {error && <p style={{ color: "#f88" }}>{error}</p>}
      <div className="gratitude-cards">
        <Metric label="Intents" value={ledger.intents_declared} />
        <Metric label="Blocked" value={ledger.guardrails_blocked} />
        <Metric label="Aligned" value={ledger.intents_aligned} />
        <Metric label="Deduped" value={ledger.duplicates_avoided} />
        <Metric label="Yielded" value={ledger.agents_yielded} />
        <Metric label="Tokens" value={ledger.tokens_saved_display} />
        <Metric label="Haiku" value={ledger.haiku_calls} />
        <Metric label="Sonnet" value={ledger.sonnet_calls} />
      </div>
      <ul className="gratitude-timeline">
        {ledger.timeline.map((item, index) => (
          <li key={`${item.at ?? index}-${item.message}`}>
            <span className="gratitude-kind">{item.kind}</span> {item.message}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="gratitude-card">
      <span className="gratitude-metric-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
