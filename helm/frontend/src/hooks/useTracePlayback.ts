import { useCallback, useEffect, useMemo, useState } from "react";

import type { FlightTrace, TraceFrame } from "../flightRecorder/types";

const DEFAULT_STEP_MS = 1400;

type Options = {
  stepMs?: number;
  autoPlay?: boolean;
};

export function useTracePlayback(trace: FlightTrace, options: Options = {}) {
  const { stepMs = DEFAULT_STEP_MS, autoPlay = false } = options;
  const frameCount = trace.frames.length;

  const [frameIndex, setFrameIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(autoPlay && frameCount > 0);

  const isComplete = frameIndex >= Math.max(0, frameCount - 1);

  const frame: TraceFrame = useMemo(
    () =>
      trace.frames[frameIndex] ??
      trace.frames[0] ?? {
        id: "empty",
        atMs: 0,
        title: "No frames",
        narration: "",
        agents: [],
        helm: { active: false },
        files: [],
      },
    [frameIndex, trace.frames],
  );

  useEffect(() => {
    setFrameIndex(0);
    setIsPlaying(autoPlay && frameCount > 0);
  }, [trace.id, autoPlay, frameCount]);

  useEffect(() => {
    if (!isPlaying || isComplete || frameCount === 0) {
      return;
    }

    const timerId = window.setTimeout(() => {
      setFrameIndex((current) => Math.min(current + 1, frameCount - 1));
    }, stepMs);

    return () => window.clearTimeout(timerId);
  }, [frameCount, frameIndex, isComplete, isPlaying, stepMs]);

  useEffect(() => {
    if (isComplete && isPlaying) {
      setIsPlaying(false);
    }
  }, [isComplete, isPlaying]);

  const play = useCallback(() => {
    if (isComplete) {
      setFrameIndex(0);
    }
    setIsPlaying(true);
  }, [isComplete]);

  const pause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const reset = useCallback(() => {
    setFrameIndex(0);
    setIsPlaying(autoPlay && frameCount > 0);
  }, [autoPlay, frameCount]);

  const stepForward = useCallback(() => {
    setIsPlaying(false);
    setFrameIndex((current) => Math.min(current + 1, frameCount - 1));
  }, [frameCount]);

  const stepBack = useCallback(() => {
    setIsPlaying(false);
    setFrameIndex((current) => Math.max(current - 1, 0));
  }, []);

  const seek = useCallback(
    (index: number) => {
      setIsPlaying(false);
      setFrameIndex(Math.min(Math.max(index, 0), Math.max(0, frameCount - 1)));
    },
    [frameCount],
  );

  return {
    frame,
    frameIndex,
    frameCount,
    isPlaying,
    isComplete,
    play,
    pause,
    reset,
    stepForward,
    stepBack,
    seek,
  };
}
