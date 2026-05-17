import { describe, expect, it } from "vitest";

import { buildDashboardModel } from "./dashboardModel";
import {
  createDemoReplayEventsForScenario,
  DEMO_SCENARIOS,
  getDemoScenario,
} from "./demoScenarios";

describe("demoScenarios", () => {
  it("registers fleet, merge, and guardrail scenarios", () => {
    expect(DEMO_SCENARIOS.map((scenario) => scenario.id)).toEqual([
      "fleet_contention",
      "merge_conflict",
      "guardrail_block",
    ]);
  });

  it("builds merge conflict incidents with resolved code", () => {
    const events = createDemoReplayEventsForScenario("merge_conflict");
    const model = buildDashboardModel(events, "replay", {
      subtitle: getDemoScenario("merge_conflict").subtitle,
    });

    const mergeIncident = model.incidents.find(
      (incident) => incident.type === "merge_conflict",
    );
    expect(mergeIncident?.status).toBe("resolved");
    expect(mergeIncident?.resolvedCode).toContain("checkout_total");
    expect(model.timeline.some((event) => event.kind === "merge_detected")).toBe(true);
    expect(model.timeline.some((event) => event.kind === "merge_resolved")).toBe(true);
  });

  it("builds guardrail scenario with blocked incident", () => {
    const events = createDemoReplayEventsForScenario("guardrail_block");
    const model = buildDashboardModel(events);

    expect(
      model.incidents.some(
        (incident) =>
          incident.type === "guardrail_block" && incident.status === "blocked",
      ),
    ).toBe(true);
  });
});
