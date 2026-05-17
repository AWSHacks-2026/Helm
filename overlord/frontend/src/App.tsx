import { useState } from "react";

import { AppShell, type AppView } from "./components/AppShell";
import { BenchmarkProof } from "./components/BenchmarkProof";
import { ControlTower } from "./components/ControlTower";
import { IncidentConsole } from "./components/IncidentConsole";
import { LandingPage } from "./components/LandingPage";
import { LegacyLabPanel } from "./components/LegacyLabPanel";
import { useDemoReplay } from "./hooks/useDemoReplay";
import { useLiveSession } from "./hooks/useLiveSession";

const SESSION_KEY = "overlord_session_id";
const DEFAULT_SESSION =
  import.meta.env.VITE_OVERLORD_TEAM_SESSION ?? "mergeai-hackathon-demo";

type DataMode = "replay" | "live";

export default function App() {
  const [view, setView] = useState<AppView>("landing");
  const [dataMode, setDataMode] = useState<DataMode>("replay");
  const [replayStarted, setReplayStarted] = useState(false);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState(
    () => localStorage.getItem(SESSION_KEY) ?? DEFAULT_SESSION,
  );
  const replayEnabled =
    dataMode === "replay" &&
    replayStarted &&
    (view === "control" || view === "incidents");
  const replay = useDemoReplay({ enabled: replayEnabled });
  const live = useLiveSession(dataMode === "live" ? sessionId : "");
  const currentModel = dataMode === "live" ? live.model : replay.model;
  const connectionLabel =
    dataMode === "live"
      ? `Live: ${live.status}`
      : replay.isComplete
        ? "Replay complete"
        : "Replay running";

  const handleStartReplay = () => {
    setDataMode("replay");
    setReplayStarted(true);
    replay.reset();
    setSelectedIncidentId(null);
    setView("control");
  };

  const handleSessionIdChange = (nextSessionId: string) => {
    setSessionId(nextSessionId);
    localStorage.setItem(SESSION_KEY, nextSessionId);
  };

  const handleOpenLiveSession = () => {
    localStorage.setItem(SESSION_KEY, sessionId);
    setDataMode("live");
    setSelectedIncidentId(null);
    setView("control");
  };

  const handleSelectIncident = (incidentId: string) => {
    setSelectedIncidentId(incidentId);
    setView("incidents");
  };

  const renderView = () => {
    if (view === "landing") {
      return (
        <LandingPage
          sessionId={sessionId}
          onSessionIdChange={handleSessionIdChange}
          onStartReplay={handleStartReplay}
          onOpenLiveSession={handleOpenLiveSession}
        />
      );
    }

    if (view === "control") {
      return (
        <ControlTower
          model={currentModel}
          connectionLabel={connectionLabel}
          onSelectIncident={handleSelectIncident}
        />
      );
    }

    if (view === "incidents") {
      return (
        <IncidentConsole
          model={currentModel}
          selectedIncidentId={selectedIncidentId}
          onSelectIncident={setSelectedIncidentId}
        />
      );
    }

    if (view === "proof") {
      return <BenchmarkProof />;
    }

    return <LegacyLabPanel />;
  };

  return (
    <AppShell view={view} onViewChange={setView}>
      {dataMode === "live" && live.error && (
        <div className="error-banner" role="alert">
          Live session error: {live.error.message}
        </div>
      )}
      {renderView()}
    </AppShell>
  );
}
