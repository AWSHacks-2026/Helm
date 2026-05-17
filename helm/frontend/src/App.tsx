import { useCallback, useEffect, useState } from "react";

import { AppShell, type AppView } from "./components/AppShell";
import { BenchmarkProof } from "./components/BenchmarkProof";
import { ControlTower } from "./components/ControlTower";
import { DemoWalkthrough } from "./components/DemoWalkthrough";
import { IncidentConsole } from "./components/IncidentConsole";
import { LandingPage } from "./components/LandingPage";
import { LegacyLabPanel } from "./components/LegacyLabPanel";
import { JUDGE_WALKTHROUGH } from "./demoWalkthrough";
import GratitudeLedgerPanel from "./GratitudeLedger";
import {
  DEFAULT_DEMO_SCENARIO_ID,
  DEMO_SCENARIOS,
  type DemoScenarioId,
} from "./orchestration/demoScenarios";
import { useDemoReplay } from "./hooks/useDemoReplay";
import { useDemoWalkthrough } from "./hooks/useDemoWalkthrough";
import { usePresenterMode } from "./hooks/usePresenterMode";
import { readInitialView, readWalkthroughFlag } from "./hooks/readInitialView";
import MissionsPanel from "./MissionsPanel";
import type { IncidentState } from "./orchestration/types";

const SESSION_KEY = "helm_session_id";
const DEFAULT_SESSION =
  import.meta.env.VITE_HELM_TEAM_SESSION ?? "mergeai-hackathon-demo";

export default function App() {
  const [view, setView] = useState<AppView>(() =>
    typeof window !== "undefined" ? readInitialView(window.location.search) : "landing",
  );
  const [replayStarted, setReplayStarted] = useState(false);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [walkthroughActive, setWalkthroughActive] = useState(() =>
    typeof window !== "undefined" ? readWalkthroughFlag(window.location.search) : false,
  );
  const [sessionId, setSessionId] = useState(
    () => localStorage.getItem(SESSION_KEY) ?? DEFAULT_SESSION,
  );
  const [demoScenarioId, setDemoScenarioId] = useState<DemoScenarioId>(
    DEFAULT_DEMO_SCENARIO_ID,
  );
  const replayActive = replayStarted;
  const replay = useDemoReplay({
    advancing: replayActive,
    scenarioId: demoScenarioId,
    sessionId,
    syncToLedger: replayActive,
  });
  const presenterMode = usePresenterMode();
  const walkthrough = useDemoWalkthrough(JUDGE_WALKTHROUGH);

  useEffect(() => {
    document.body.classList.toggle("presenter-mode", presenterMode);
    return () => document.body.classList.remove("presenter-mode");
  }, [presenterMode]);

  const connectionLabel = replay.isComplete ? "Replay complete" : "Replay running";

  const pickIncidentForStep = useCallback(
    (incidents: IncidentState[], type?: IncidentState["type"]) => {
      if (!type) return incidents[0]?.id ?? null;
      return incidents.find((incident) => incident.type === type)?.id ?? incidents[0]?.id ?? null;
    },
    [],
  );

  const handleStartReplay = () => {
    setDemoScenarioId(DEFAULT_DEMO_SCENARIO_ID);
    setReplayStarted(true);
    replay.reset();
    setSelectedIncidentId(null);
    setView("control");
  };

  const handleStartJudgeDemo = () => {
    handleStartReplay();
    walkthrough.reset();
    setWalkthroughActive(true);
    setView("control");
  };

  const handleWalkthroughAdvance = () => {
    const nextIndex = Math.min(walkthrough.index + 1, walkthrough.total - 1);
    const nextStep = JUDGE_WALKTHROUGH[nextIndex];
    if (!nextStep) return;

    if (walkthrough.index < walkthrough.total - 1) {
      walkthrough.advance();
    }

    setView(nextStep.view);
    if (nextStep.view === "incidents") {
      setSelectedIncidentId(
        pickIncidentForStep(replay.model.incidents, nextStep.selectIncidentType),
      );
    }
  };

  const handleSessionIdChange = (nextSessionId: string) => {
    setSessionId(nextSessionId);
    localStorage.setItem(SESSION_KEY, nextSessionId);
  };

  const handleSelectIncident = (incidentId: string) => {
    setSelectedIncidentId(incidentId);
    setView("incidents");
  };

  const handleDemoScenarioChange = (nextScenarioId: DemoScenarioId) => {
    setDemoScenarioId(nextScenarioId);
    replay.reset();
    setSelectedIncidentId(null);
  };

  const renderView = () => {
    if (view === "landing") {
      return (
        <LandingPage
          sessionId={sessionId}
          onSessionIdChange={handleSessionIdChange}
          onStartReplay={handleStartReplay}
          onStartJudgeDemo={handleStartJudgeDemo}
        />
      );
    }

    if (view === "control") {
      return (
        <ControlTower
          model={replay.model}
          connectionLabel={connectionLabel}
          demoScenarios={DEMO_SCENARIOS}
          activeDemoScenarioId={demoScenarioId}
          onDemoScenarioChange={handleDemoScenarioChange}
          onSelectIncident={handleSelectIncident}
        />
      );
    }

    if (view === "incidents") {
      return (
        <IncidentConsole
          model={replay.model}
          selectedIncidentId={selectedIncidentId}
          onSelectIncident={setSelectedIncidentId}
        />
      );
    }

    if (view === "missions") {
      return <MissionsPanel sessionId={sessionId} />;
    }

    if (view === "gratitude") {
      return <GratitudeLedgerPanel sessionId={sessionId} />;
    }

    if (view === "proof") {
      return <BenchmarkProof />;
    }

    return <LegacyLabPanel />;
  };

  return (
    <AppShell view={view} onViewChange={setView}>
      {renderView()}
      {walkthroughActive && walkthrough.step && view !== "landing" && (
        <DemoWalkthrough
          step={walkthrough.step}
          index={walkthrough.index}
          total={walkthrough.total}
          isComplete={walkthrough.isComplete}
          onAdvance={handleWalkthroughAdvance}
          onDismiss={() => setWalkthroughActive(false)}
        />
      )}
    </AppShell>
  );
}
