import { useCallback, useEffect, useMemo, useState } from "react";

import { createDemoReplayEvents } from "../orchestration/demoReplay";
import { buildDashboardModel } from "../orchestration/dashboardModel";
import type { DashboardModel, TimelineEvent } from "../orchestration/types";

const REPLAY_STEP_MS = 1200;

const initialVisibleCount = (events: TimelineEvent[]): number =>
  events.length > 0 ? 1 : 0;

interface UseDemoReplayOptions {
  enabled?: boolean;
}

export function useDemoReplay(options: UseDemoReplayOptions = {}): {
  model: DashboardModel;
  isPlaying: boolean;
  isComplete: boolean;
  play: () => void;
  pause: () => void;
  reset: () => void;
} {
  const { enabled = true } = options;
  const [events] = useState<TimelineEvent[]>(() => createDemoReplayEvents());
  const [visibleCount, setVisibleCount] = useState(() =>
    initialVisibleCount(events),
  );
  const [isPlaying, setIsPlaying] = useState(() => events.length > 0);
  const isComplete = visibleCount >= events.length;

  useEffect(() => {
    if (!enabled || !isPlaying || isComplete) {
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
  }, [enabled, events.length, isComplete, isPlaying, visibleCount]);

  const visibleEvents = useMemo(
    () => events.slice(0, visibleCount),
    [events, visibleCount],
  );
  const model = useMemo(
    () => buildDashboardModel(visibleEvents, "replay"),
    [visibleEvents],
  );

  const play = useCallback(() => {
    setIsPlaying(!isComplete);
  }, [isComplete]);

  const pause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const reset = useCallback(() => {
    setVisibleCount(initialVisibleCount(events));
    setIsPlaying(events.length > 0);
  }, [events]);

  return {
    model,
    isPlaying,
    isComplete,
    play,
    pause,
    reset,
  };
}
