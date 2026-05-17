import { useCallback, useEffect, useState } from "react";

import { humanizeTrace } from "../../flightRecorder/humanizeTrace";
import {
  getTraceScenario,
  TRACE_SCENARIOS,
  type TraceScenarioId,
} from "../../flightRecorder/traceCatalog";
import type { FlightTrace } from "../../flightRecorder/types";
import { useTracePlayback } from "../../hooks/useTracePlayback";
import "../../styles/flight-recorder.css";
import { LiveRunStats } from "./LiveRunStats";
import { TraceFilePanel } from "./TraceFilePanel";
import { TraceGraph } from "./TraceGraph";
import { TraceScrubber } from "./TraceScrubber";

export function FlightRecorderPage() {
  const [scenarioId, setScenarioId] = useState<TraceScenarioId>("contention_n2_live_helm");
  const [trace, setTrace] = useState<FlightTrace | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadTrace = useCallback(async (id: TraceScenarioId) => {
    setLoadError(null);
    try {
      const scenario = getTraceScenario(id);
      const loaded = await scenario.load();
      setTrace(humanizeTrace(loaded));
    } catch (err) {
      setTrace(null);
      setLoadError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void loadTrace(scenarioId);
  }, [loadTrace, scenarioId]);

  const playback = useTracePlayback(trace ?? emptyTrace(), { autoPlay: false });

  const handleScenarioChange = (nextId: string) => {
    setScenarioId(nextId as TraceScenarioId);
  };

  return (
    <main className="flight-recorder page-enter">
      <header className="screen-header">
        <div>
          <p className="eyebrow">Demo · coordination internals</p>
          <h1>Under the hood</h1>
          <p>{trace?.description ?? "Loading trace…"}</p>
        </div>
      </header>

      <div className="flight-recorder-toolbar">
        <label>
          Scenario
          <select
            value={scenarioId}
            onChange={(event) => handleScenarioChange(event.target.value)}
          >
            {TRACE_SCENARIOS.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.label}
              </option>
            ))}
          </select>
        </label>
        {loadError && <p className="trace-load-error">{loadError}</p>}
      </div>

      <LiveRunStats meta={trace?.meta} />

      {trace && (
        <>
          <TraceGraph frame={playback.frame} />
          <TraceFilePanel file={playback.frame.files[0]} />
          <p className="trace-narration">{playback.frame.narration}</p>
          <TraceScrubber trace={trace} playback={playback} />
        </>
      )}
    </main>
  );
}

function emptyTrace(): FlightTrace {
  return {
    id: "empty",
    label: "…",
    description: "",
    frames: [
      {
        id: "empty",
        atMs: 0,
        title: "Loading",
        narration: "",
        agents: [],
        helm: { active: false },
        edges: [],
        files: [],
      },
    ],
  };
}
