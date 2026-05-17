import { describe, expect, it } from "vitest";

import { TRACE_SCENARIOS, getTraceScenario } from "./traceCatalog";

describe("traceCatalog", () => {
  it("loads two N=2 scenarios with helm intervention frames", () => {
    expect(TRACE_SCENARIOS.map((scenario) => scenario.id)).toContain(
      "contention_n2_live_helm",
    );
    expect(TRACE_SCENARIOS.map((scenario) => scenario.id)).toContain(
      "contention_n2_live_baseline",
    );
    expect(TRACE_SCENARIOS.map((scenario) => scenario.id)).toContain("merge_n2");
    const dedup = getTraceScenario("contention_n2").load();
    const merge = getTraceScenario("merge_n2").load();
    expect(dedup.frames.some((frame) => frame.helm.action === "dedup")).toBe(true);
    expect(merge.frames.some((frame) => frame.files[0]?.status === "conflict")).toBe(
      true,
    );
    expect(dedup.frames[0].agents).toHaveLength(2);
  });
});
