import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  DEFAULT_DEMO_SCENARIO_ID,
  getDemoScenario,
  type DemoScenarioId,
} from "../orchestration/demoScenarios";
import { buildDashboardModel } from "../orchestration/dashboardModel";
import { syncReplayEventToLedger } from "../orchestration/syncReplayToLedger";
import type { DashboardModel, TimelineEvent } from "../orchestration/types";

const REPLAY_STEP_MS = 1200;

const initialVisibleCount = (events: TimelineEvent[]): number =>
  events.length > 0 ? 1 : 0;

interface UseDemoReplayOptions {
  /** Advance replay timeline (runs in background once demo started). */
  advancing?: boolean;
  scenarioId?: DemoScenarioId;
  sessionId?: string;
  syncToLedger?: boolean;
}

async function syncEventToLedger(
  sessionId: string,
  event: TimelineEvent,
  syncedEventIds: Set<string>,
): Promise<void> {
  if (syncedEventIds.has(event.id)) return;
  syncedEventIds.add(event.id);
  try {
    await syncReplayEventToLedger(sessionId, event);
  } catch {
    syncedEventIds.delete(event.id);
    throw new Error(`Failed to sync replay event ${event.id}`);
  }
}

export function useDemoReplay(options: UseDemoReplayOptions = {}): {
  model: DashboardModel;
  scenarioId: DemoScenarioId;
  isPlaying: boolean;
  isComplete: boolean;
  play: () => void;
  pause: () => void;
  reset: () => void;
} {
  const {
    advancing = true,
    scenarioId = DEFAULT_DEMO_SCENARIO_ID,
    sessionId = "",
    syncToLedger = false,
  } = options;
  const scenario = useMemo(() => getDemoScenario(scenarioId), [scenarioId]);
  const syncedEventIds = useRef<Set<string>>(new Set());
  const scenarioReadyRef = useRef(scenarioId);
  const [events, setEvents] = useState<TimelineEvent[]>(() => scenario.createEvents());
  const [visibleCount, setVisibleCount] = useState(() =>
    initialVisibleCount(events),
  );
  const [isPlaying, setIsPlaying] = useState(() => events.length > 0);
  const isComplete = visibleCount >= events.length;

  useEffect(() => {
    if (scenarioReadyRef.current === scenarioId) {
      return;
    }
    scenarioReadyRef.current = scenarioId;
    const nextEvents = scenario.createEvents();
    syncedEventIds.current.clear();
    setEvents(nextEvents);
    setVisibleCount(initialVisibleCount(nextEvents));
    setIsPlaying(nextEvents.length > 0);
  }, [scenario, scenarioId]);

  useEffect(() => {
    if (!advancing || !isPlaying || isComplete) {
      return;
    }

    const timerId = setTimeout(() => {
      const nextCount = Math.min(visibleCount + 1, events.length);

      setVisibleCount(nextCount);

      if (nextCount >= events.length) {
        setIsPlaying(false);
      }
    }, REPLAY_STEP_MS);

    return () => {
      clearTimeout(timerId);
    };
  }, [advancing, events.length, isComplete, isPlaying, visibleCount]);

  useEffect(() => {
    if (!syncToLedger || !sessionId) return;

    const visible = events.slice(0, visibleCount);
    for (const event of visible) {
      void syncEventToLedger(sessionId, event, syncedEventIds.current).catch(() => {
        /* best-effort per step; completion effect retries all */
      });
    }
  }, [events, sessionId, syncToLedger, visibleCount]);

  useEffect(() => {
    if (!isComplete || !syncToLedger || !sessionId) return;

    void (async () => {
      for (const event of events) {
        try {
          await syncEventToLedger(sessionId, event, syncedEventIds.current);
        } catch {
          /* continue remaining events */
        }
      }
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("helm-ledger-updated"));
      }
    })();
  }, [events, isComplete, sessionId, syncToLedger]);

  const visibleEvents = useMemo(
    () => events.slice(0, visibleCount),
    [events, visibleCount],
  );
  const model = useMemo(
    () =>
      buildDashboardModel(visibleEvents, "replay", {
        subtitle: scenario.subtitle,
        completeHint: scenario.completeHint,
      }),
    [scenario.completeHint, scenario.subtitle, visibleEvents],
  );

  const play = useCallback(() => {
    setIsPlaying(!isComplete);
  }, [isComplete]);

  const pause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const reset = useCallback(() => {
    syncedEventIds.current.clear();
    const nextEvents = scenario.createEvents();
    setEvents(nextEvents);
    setVisibleCount(initialVisibleCount(nextEvents));
    setIsPlaying(nextEvents.length > 0);
  }, [scenario]);

  return {
    model,
    scenarioId: scenario.id,
    isPlaying,
    isComplete,
    play,
    pause,
    reset,
  };
}
