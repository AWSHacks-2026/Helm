import { useCallback, useEffect, useState } from "react";
import {
  delegateMissions,
  fetchMissions,
  MissionSummary,
  startMission,
} from "./api/missions";
import { useConflictStream } from "./hooks/useConflictStream";

const AGENT_ID =
  import.meta.env.VITE_OVERLORD_AGENT_ID ?? "agent_local";

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
      (msg: unknown) => {
        const event = msg as { type?: string };
        if (event?.type === "missions_updated") {
          refresh();
        }
      },
      [refresh]
    )
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
    <section className="missions-panel">
      <h2>Missions (GitHub)</h2>
      <p className="missions-meta">
        This laptop: <strong>{AGENT_ID}</strong>
      </p>
      {error && <p style={{ color: "#f88" }}>{error}</p>}
      <button type="button" onClick={handleDelegate} disabled={delegating}>
        {delegating ? "Delegating…" : "Delegate all"}
      </button>
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
              <td>{m.file_path || "—"}</td>
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
      {missions.length === 0 && <p>No missions for this session.</p>}
    </section>
  );
}
