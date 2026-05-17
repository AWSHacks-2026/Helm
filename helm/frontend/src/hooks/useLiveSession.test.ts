import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const liveSessionFixture = vi.hoisted(() => {
  const events = [
    {
      id: "event-001",
      timestamp: "2026-05-16T16:00:00.000Z",
      kind: "agent_started" as const,
      title: "Agent 01 started live work",
      description: "Agent 01 began live session work.",
      agent: {
        id: "agent-01",
        name: "Agent 01",
        status: "coding" as const,
        taskTitle: "Live session task",
      },
    },
  ];

  return {
    events,
    fetchLiveSessionEvents: vi.fn(),
    useConflictStream: vi.fn(),
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
  type CallbackEntry<T> = {
    deps: unknown[] | undefined;
    value: T;
  };
  type Ref<T> = {
    current: T;
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
  let callbacks: CallbackEntry<unknown>[] = [];
  let refs: Ref<unknown>[] = [];
  let stateIndex = 0;
  let effectIndex = 0;
  let memoIndex = 0;
  let callbackIndex = 0;
  let refIndex = 0;

  return {
    beginRender() {
      stateIndex = 0;
      effectIndex = 0;
      memoIndex = 0;
      callbackIndex = 0;
      refIndex = 0;
    },
    reset() {
      for (const effect of effects) {
        effect.cleanup?.();
      }

      states = [];
      effects = [];
      memos = [];
      callbacks = [];
      refs = [];
      stateIndex = 0;
      effectIndex = 0;
      memoIndex = 0;
      callbackIndex = 0;
      refIndex = 0;
    },
    useCallback<T extends (...args: never[]) => unknown>(
      callback: T,
      deps?: unknown[],
    ): T {
      const index = callbackIndex++;
      const current = callbacks[index] as CallbackEntry<T> | undefined;

      if (!current || depsChanged(current.deps, deps)) {
        callbacks[index] = { deps, value: callback };
        return callback;
      }

      return current.value;
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
    useRef<T>(initialValue: T): Ref<T> {
      const index = refIndex++;

      if (refs.length <= index) {
        refs[index] = { current: initialValue };
      }

      return refs[index] as Ref<T>;
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
  useRef: hookHarness.useRef,
  useState: hookHarness.useState,
}));

vi.mock("../api/orchestration", () => ({
  fetchLiveSessionEvents: liveSessionFixture.fetchLiveSessionEvents,
}));

vi.mock("./useConflictStream", () => ({
  useConflictStream: liveSessionFixture.useConflictStream,
}));

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("useLiveSession", () => {
  beforeEach(() => {
    hookHarness.reset();
    liveSessionFixture.fetchLiveSessionEvents.mockReset();
    liveSessionFixture.useConflictStream.mockClear();
  });

  afterEach(() => {
    hookHarness.reset();
  });

  it("marks the session connected after a successful refresh recovers from an error", async () => {
    const { useLiveSession } = await import("./useLiveSession");
    liveSessionFixture.fetchLiveSessionEvents
      .mockRejectedValueOnce(new Error("backend unavailable"))
      .mockResolvedValue(liveSessionFixture.events);

    hookHarness.beginRender();
    let live = useLiveSession("session-1");
    await flushPromises();

    hookHarness.beginRender();
    live = useLiveSession("session-1");
    expect(live.status).toBe("error");
    expect(live.error?.message).toBe("backend unavailable");

    await live.refresh();
    hookHarness.beginRender();
    live = useLiveSession("session-1");

    expect(live.status).toBe("connected");
    expect(live.error).toBeNull();
    expect(live.model.timeline.map((event) => event.id)).toEqual(["event-001"]);
  });
});
