import { describe, expect, it } from "vitest";

import type { FlightTrace } from "./types";
import { TRACE_SCENARIOS, getTraceScenario } from "./traceCatalog";

function loadSyncTrace(id: Parameters<typeof getTraceScenario>[0]): FlightTrace {
  const loaded = getTraceScenario(id).load();
  if (loaded instanceof Promise) {
    throw new Error(`expected sync trace loader for ${id}`);
  }
  return loaded;
}

describe("traceCatalog", () => {
  it("loads scripted N=2 scenarios with helm intervention frames", () => {
    expect(TRACE_SCENARIOS.map((scenario) => scenario.id)).toContain(
      "contention_n2_live_helm",
    );
    expect(TRACE_SCENARIOS.map((scenario) => scenario.id)).toContain(
      "contention_n2_live_baseline",
    );
    expect(TRACE_SCENARIOS.map((scenario) => scenario.id)).toContain("merge_n2");
    const dedup = loadSyncTrace("contention_n2");
    const merge = loadSyncTrace("merge_n2");
    expect(dedup.frames.some((frame) => frame.helm.action === "dedup")).toBe(true);
    expect(merge.frames.some((frame) => frame.files[0]?.status === "conflict")).toBe(
      true,
    );
    expect(dedup.frames[0].agents).toHaveLength(2);
  });

  it("registers async live trace loaders", () => {
    const live = getTraceScenario("contention_n2_live_helm");
    expect(live.load).toBeTypeOf("function");
    expect(live.label).toMatch(/Live/i);
  });
});
