import { useCallback, useEffect, useState } from "react";

import {
  delegateMissions,
  fetchMissions,
  type MissionSummary,
  startMission,
} from "./api/missions";
import { MISSIONS_INTRO } from "./content/gratitudeMission";
import { useConflictStream, type ConflictStreamMessage } from "./hooks/useConflictStream";

const AGENT_ID = import.meta.env.VITE_HELM_AGENT_ID ?? "agent_local";

type Props = {
  sessionId: string;
  onRefresh?: () => void;
};

export default function MissionsPanel({ sessionId, onRefresh }: Props) {
  const [missions, setMissions] = useState<MissionSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [delegating, setDelegating] = useState(false);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      setError(null);
      setMissions(await fetchMissions(sessionId));
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
    useCallback(
      (msg: ConflictStreamMessage) => {
        const payload =
          msg.type === "message" && typeof msg.payload === "object" && msg.payload !== null
            ? (msg.payload as { type?: string })
            : null;
        if (payload?.type === "missions_updated") {
          refresh();
        }
      },
      [refresh],
    ),
  );

  const handleDelegate = async () => {
    setDelegating(true);
    try {
      await delegateMissions(sessionId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDelegating(false);
    }
  };

  return (
    <main className="missions-page">
      <header className="screen-header">
        <div>
          <p className="eyebrow">{MISSIONS_INTRO.eyebrow}</p>
          <h1>{MISSIONS_INTRO.title}</h1>
          <p>{MISSIONS_INTRO.body}</p>
        </div>
      </header>

      <section className="missions-panel" aria-labelledby="missions-queue-title">
        <header className="missions-toolbar">
          <div>
            <h2 id="missions-queue-title">GitHub mission queue</h2>
            <p className="missions-meta">
              This laptop: <strong>{AGENT_ID}</strong>
              {sessionId && (
                <>
                  {" "}
                  · session <code>{sessionId}</code>
                </>
              )}
            </p>
          </div>
          <button type="button" onClick={handleDelegate} disabled={delegating || !sessionId}>
            {delegating ? "Delegating…" : "Delegate all"}
          </button>
        </header>

        {error && <p className="demo-error">{error}</p>}

        <div className="missions-table-wrap">
          <table className="missions-table">
            <thead>
              <tr>
                <th>Issue</th>
                <th>Title</th>
                <th>File</th>
                <th>Agent</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {missions.map((m) => (
                <tr key={m.mission_id}>
                  <td>{m.external_id ?? "—"}</td>
                  <td>{m.title}</td>
                  <td>
                    <code>{m.file_path || "—"}</code>
                  </td>
                  <td>{m.assigned_agent_id ?? "—"}</td>
                  <td>{m.status}</td>
                  <td>
                    <button
                      type="button"
                      disabled={m.status === "in_progress" || m.status === "done"}
                      onClick={async () => {
                        try {
                          await startMission(m.mission_id, sessionId, AGENT_ID);
                          await refresh();
                        } catch (err) {
                          setError(err instanceof Error ? err.message : String(err));
                        }
                      }}
                    >
                      Start
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {missions.length === 0 && (
          <p className="missions-empty">
            No missions yet. Run{" "}
            <code>./scripts/demo_github_delegation.sh</code> to load issues, then delegate.
            Counters on <strong>Gratitude</strong> update when Helm trims overlap.
          </p>
        )}
      </section>
    </main>
  );
}
