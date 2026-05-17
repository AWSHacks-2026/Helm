import { describe, expect, it } from "vitest";

import { buildDashboardModel } from "./dashboardModel";
import { createShopfixDemoReplayEvents } from "./shopfixDemoReplay";

describe("shopfixDemoReplay", () => {
  it("uses shopfix auth paths", () => {
    const events = createShopfixDemoReplayEvents();
    const serialized = JSON.stringify(events);
    expect(serialized).toContain("backend/app/routers/auth.py");
    expect(events.some((event) => event.kind === "duplicate_detected")).toBe(true);
    expect(events.some((event) => event.kind === "guardrail_blocked")).toBe(true);
  });

  it("ends with coordinated fleet health after full replay", () => {
    const model = buildDashboardModel(createShopfixDemoReplayEvents());

    expect(
      model.incidents.find((incident) => incident.id === "incident-auth-dedup")?.status,
    ).toBe("resolved");
    expect(model.metrics.openIncidents).toBe(0);
    expect(model.metrics.projectHealth).toBe("clean");
    expect(model.timeline.at(-1)?.title).toContain("Fleet coordinated");
  });
});
