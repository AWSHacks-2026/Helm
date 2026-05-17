import { useCallback, useEffect, useState } from "react";
import {
  approveConflict,
  ConflictSummary,
  fetchConflictDetail,
  fetchConflicts,
  fetchHistory,
  ResolveDetail,
} from "./api/client";
import DemoLab from "./DemoLab";
import MergeLab from "./MergeLab";
import GratitudeLedgerPanel from "./GratitudeLedger";
import MissionsPanel from "./MissionsPanel";
import { useConflictStream } from "./hooks/useConflictStream";

const SESSION_KEY = "overlord_session_id";
const DEFAULT_SESSION =
  import.meta.env.VITE_OVERLORD_TEAM_SESSION ?? "mergeai-hackathon-demo";

type Tab = "dashboard" | "demo" | "merge";

function Dashboard() {
  const [sessionId, setSessionId] = useState(
    () => localStorage.getItem(SESSION_KEY) ?? DEFAULT_SESSION
  );
  const [conflicts, setConflicts] = useState<ConflictSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ResolveDetail | null>(null);
  const [history, setHistory] = useState<unknown[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      setError(null);
      const [list, hist] = await Promise.all([
        fetchConflicts(sessionId),
        fetchHistory(sessionId),
      ]);
      setConflicts(list);
      setHistory(hist);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [sessionId]);

  useEffect(() => {
    localStorage.setItem(SESSION_KEY, sessionId);
    refresh();
  }, [sessionId, refresh]);

  useConflictStream(
    sessionId,
    useCallback(() => {
      refresh();
    }, [refresh])
  );

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    fetchConflictDetail(selectedId)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [selectedId]);

  const tokensSaved = detail?.resolution.tokens_saved_estimate ?? "—";

  return (
    <div className="app">
      <div className="panel">
        <h2>Session</h2>
        <input
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
          placeholder="session_id"
        />
        <p>Tokens saved (latest): {tokensSaved}</p>
        <GratitudeLedgerPanel sessionId={sessionId} onRefresh={refresh} />
        <MissionsPanel sessionId={sessionId} onRefresh={refresh} />
        <h2>Conflicts</h2>
        {error && <p style={{ color: "#f88" }}>{error}</p>}
        {conflicts.map((c) => (
          <div
            key={c.conflict_id}
            className={`conflict-item ${selectedId === c.conflict_id ? "active" : ""}`}
            onClick={() => setSelectedId(c.conflict_id)}
          >
            {c.file_path} — {c.status}
          </div>
        ))}
      </div>

      <div className="panel">
        <h2>Conflict detail</h2>
        {!detail && <p>Select a conflict</p>}
        {detail && (
          <>
            <p>
              <strong>{detail.file_path}</strong> ({detail.status})
            </p>
            <h3>Agent A</h3>
            <pre>
              {detail.agent_a.intent}
              {"\n\n"}
              {detail.agent_a.code}
            </pre>
            <h3>Agent B</h3>
            <pre>
              {detail.agent_b.intent}
              {"\n\n"}
              {detail.agent_b.code}
            </pre>
            <h3>Resolution</h3>
            <pre>{detail.resolution.reasoning}</pre>
            <pre>{detail.resolution.resolved_code}</pre>
            <button
              type="button"
              onClick={async () => {
                await approveConflict(detail.conflict_id, true);
                refresh();
              }}
            >
              Approve
            </button>
            <button
              type="button"
              onClick={async () => {
                await approveConflict(detail.conflict_id, false);
                refresh();
              }}
            >
              Reject
            </button>
          </>
        )}
      </div>

      <div className="panel">
        <h2>History</h2>
        <pre>{JSON.stringify(history, null, 2)}</pre>
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("merge");

  return (
    <>
      <nav className="app-nav">
        <button
          type="button"
          className={tab === "merge" ? "active" : ""}
          onClick={() => setTab("merge")}
        >
          Merge lab
        </button>
        <button
          type="button"
          className={tab === "demo" ? "active" : ""}
          onClick={() => setTab("demo")}
        >
          Demo lab
        </button>
        <button
          type="button"
          className={tab === "dashboard" ? "active" : ""}
          onClick={() => setTab("dashboard")}
        >
          Dashboard
        </button>
      </nav>
      {tab === "merge" ? (
        <div className="app app-merge">
          <MergeLab />
        </div>
      ) : tab === "demo" ? (
        <div className="app app-demo">
          <DemoLab />
        </div>
      ) : (
        <Dashboard />
      )}
    </>
  );
}
