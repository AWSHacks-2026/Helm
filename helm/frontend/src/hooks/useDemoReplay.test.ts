import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const replayFixture = vi.hoisted(() => {
  const events = [
    {
      id: "event-001",
      timestamp: "2026-05-16T16:00:00.000Z",
      kind: "agent_started" as const,
      title: "Agent 01 started auth work",
      description: "Agent 01 began auth work.",
      agent: {
        id: "agent-01",
        name: "Agent 01",
        status: "coding" as const,
        taskTitle: "Auth session hardening",
      },
    },
    {
      id: "event-002",
      timestamp: "2026-05-16T16:00:15.000Z",
      kind: "agent_started" as const,
      title: "Agent 02 started catalog work",
      description: "Agent 02 began catalog work.",
      agent: {
        id: "agent-02",
        name: "Agent 02",
        status: "coding" as const,
        taskTitle: "Catalog facets",
      },
    },
    {
      id: "event-003",
      timestamp: "2026-05-16T16:00:30.000Z",
      kind: "benchmark_result" as const,
      title: "Token benchmark completed",
      description: "Helm replay reduced coordination tokens.",
      benchmark: {
        tokenSavingsLabel: "42%",
        baselineTokens: 42000,
        overlordTokens: 24360,
      },
    },
  ];

  return {
    createDemoReplayEvents: vi.fn(() => events),
    events,
  };
});

const hookHarness = vi.hoisted(() => {
  type Cleanup = () => void;
  type EffectEntry = {
    deps: unknown[] | undefined;
    cleanup?: Cleanup;
  };
  type MemoEntry<T> = {
    deps: unknown[] | undefined;
    value: T;
  };

  const depsChanged = (
    previous: unknown[] | undefined,
    next: unknown[] | undefined,
  ): boolean => {
    if (!previous || !next) return true;
    if (previous.length !== next.length) return true;

    return previous.some((value, index) => !Object.is(value, next[index]));
  };

  let states: unknown[] = [];
  let effects: EffectEntry[] = [];
  let memos: MemoEntry<unknown>[] = [];
  let stateIndex = 0;
  let effectIndex = 0;
  let memoIndex = 0;

  return {
    beginRender() {
      stateIndex = 0;
      effectIndex = 0;
      memoIndex = 0;
    },
    reset() {
      for (const effect of effects) {
        effect.cleanup?.();
      }

      states = [];
      effects = [];
      memos = [];
      stateIndex = 0;
      effectIndex = 0;
      memoIndex = 0;
    },
    unmount() {
      for (const effect of effects) {
        effect.cleanup?.();
      }

      effects = [];
    },
    useCallback<T extends (...args: never[]) => unknown>(callback: T): T {
      return callback;
    },
    useEffect(effect: () => void | Cleanup, deps?: unknown[]) {
      const index = effectIndex++;
      const current = effects[index];

      if (!current || depsChanged(current.deps, deps)) {
        current?.cleanup?.();
        const cleanup = effect();
        effects[index] = {
          deps,
          cleanup: typeof cleanup === "function" ? cleanup : undefined,
        };
      }
    },
    useMemo<T>(factory: () => T, deps?: unknown[]): T {
      const index = memoIndex++;
      const current = memos[index] as MemoEntry<T> | undefined;

      if (!current || depsChanged(current.deps, deps)) {
        const value = factory();
        memos[index] = { deps, value };
        return value;
      }

      return current.value;
    },
    useState<T>(
      initialValue: T | (() => T),
    ): [T, (nextValue: T | ((currentValue: T) => T)) => void] {
      const index = stateIndex++;

      if (states.length <= index) {
        states[index] =
          typeof initialValue === "function"
            ? (initialValue as () => T)()
            : initialValue;
      }

      return [
        states[index] as T,
        (nextValue) => {
          states[index] =
            typeof nextValue === "function"
              ? (nextValue as (currentValue: T) => T)(states[index] as T)
              : nextValue;
        },
      ];
    },
  };
});

vi.mock("react", () => ({
  useCallback: hookHarness.useCallback,
  useEffect: hookHarness.useEffect,
  useMemo: hookHarness.useMemo,
  useRef: <T,>(initialValue: T) => ({ current: initialValue }),
  useState: hookHarness.useState,
}));

vi.mock("../orchestration/demoScenarios", () => ({
  DEFAULT_DEMO_SCENARIO_ID: "fleet_contention",
  getDemoScenario: () => ({
    id: "fleet_contention",
    label: "Fleet dedup",
    subtitle: "test",
    completeHint: "done",
    createEvents: replayFixture.createDemoReplayEvents,
  }),
}));

describe("useDemoReplay", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    hookHarness.reset();
    replayFixture.createDemoReplayEvents.mockClear();
  });

  afterEach(() => {
    hookHarness.reset();
    vi.useRealTimers();
  });

  it("starts with the first replay event visible and reuses the fixture", async () => {
    const { useDemoReplay } = await import("./useDemoReplay");

    hookHarness.beginRender();
    const firstRender = useDemoReplay();
    hookHarness.beginRender();
    const secondRender = useDemoReplay();

    expect(firstRender.model.mode).toBe("replay");
    expect(firstRender.model.timeline.map((event) => event.id)).toEqual([
      "event-001",
    ]);
    expect(firstRender.isPlaying).toBe(true);
    expect(firstRender.isComplete).toBe(false);
    expect(secondRender.model.timeline.map((event) => event.id)).toEqual([
      "event-001",
    ]);
    expect(replayFixture.createDemoReplayEvents).toHaveBeenCalledTimes(1);
  });

  it("reveals events on playback, supports pause/play, and resets to playback", async () => {
    const { useDemoReplay } = await import("./useDemoReplay");

    hookHarness.beginRender();
    let replay = useDemoReplay();

    vi.advanceTimersByTime(1199);
    hookHarness.beginRender();
    replay = useDemoReplay();
    expect(replay.model.timeline.map((event) => event.id)).toEqual(["event-001"]);

    vi.advanceTimersByTime(1);
    hookHarness.beginRender();
    replay = useDemoReplay();
    expect(replay.model.timeline.map((event) => event.id)).toEqual([
      "event-001",
      "event-002",
    ]);

    replay.pause();
    hookHarness.beginRender();
    replay = useDemoReplay();
    vi.advanceTimersByTime(1200);
    hookHarness.beginRender();
    replay = useDemoReplay();
    expect(replay.isPlaying).toBe(false);
    expect(replay.model.timeline.map((event) => event.id)).toEqual([
      "event-001",
      "event-002",
    ]);

    replay.play();
    hookHarness.beginRender();
    replay = useDemoReplay();
    vi.advanceTimersByTime(1200);
    hookHarness.beginRender();
    replay = useDemoReplay();
    expect(replay.isComplete).toBe(true);
    expect(replay.isPlaying).toBe(false);
    expect(replay.model.timeline.map((event) => event.id)).toEqual(
      replayFixture.events.map((event) => event.id),
    );

    replay.reset();
    hookHarness.beginRender();
    replay = useDemoReplay();
    expect(replay.isPlaying).toBe(true);
    expect(replay.isComplete).toBe(false);
    expect(replay.model.timeline.map((event) => event.id)).toEqual(["event-001"]);
  });

  it("cleans up playback timers on unmount", async () => {
    const { useDemoReplay } = await import("./useDemoReplay");

    hookHarness.beginRender();
    useDemoReplay();
    expect(vi.getTimerCount()).toBe(1);

    hookHarness.unmount();

    expect(vi.getTimerCount()).toBe(0);
  });

  it("does not schedule playback timers when disabled", async () => {
    const { useDemoReplay } = await import("./useDemoReplay");

    hookHarness.beginRender();
    let replay = useDemoReplay({ advancing: false });
    expect(replay.isPlaying).toBe(true);
    expect(vi.getTimerCount()).toBe(0);

    vi.advanceTimersByTime(1200);
    hookHarness.beginRender();
    replay = useDemoReplay({ advancing: false });

    expect(replay.model.timeline.map((event) => event.id)).toEqual(["event-001"]);
    expect(vi.getTimerCount()).toBe(0);
  });
});
