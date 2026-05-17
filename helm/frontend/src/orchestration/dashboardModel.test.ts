import { describe, expect, it } from "vitest";

import { createDemoReplayEvents } from "./demoReplay";
import { buildDashboardModel } from "./dashboardModel";
import type { TimelineEvent } from "./types";

describe("buildDashboardModel", () => {
  it("summarizes demo replay activity for the control tower", () => {
    const model = buildDashboardModel(createDemoReplayEvents());

    expect(model.agents).toHaveLength(6);
    expect(model.metrics.activeAgents).toBeGreaterThan(0);
    expect(model.metrics.activeAgents).toBe(5);
    expect(model.metrics.reassignedAgents).toBe(1);
    expect(model.metrics.tokenSavingsLabel).toBe("42%");
    expect(model.metrics.projectHealth).toBe("needs_review");
    expect(model.metrics.overlordActions).toBeGreaterThanOrEqual(4);
    expect(model.timeline.map((event) => event.kind)).toEqual(
      expect.arrayContaining([
        "duplicate_detected",
        "guardrail_blocked",
        "merge_resolved",
      ]),
    );
    expect(model.incidents.map((incident) => incident.type)).toContain(
      "duplicate_work",
    );
    expect(
      model.incidents.some((incident) => incident.status === "open"),
    ).toBe(true);
  });

  it("keeps replay coverage across demo domains and incidents", () => {
    const model = buildDashboardModel(createDemoReplayEvents());
    const coverageText = model.agents
      .map((agent) => `${agent.filePath ?? ""} ${agent.taskTitle}`)
      .join(" ");
    const agent05 = model.agents.find((agent) => agent.id === "agent-05");
    const billingMergeIncident = model.incidents.find(
      (incident) => incident.id === "incident-billing-merge",
    );

    expect(coverageText).toContain("auth");
    expect(coverageText).toContain("catalog");
    expect(coverageText).toContain("billing");
    expect(coverageText).toContain("cache");
    expect(coverageText).toContain("search");
    expect(agent05?.status).toBe("blocked");
    expect(billingMergeIncident?.status).toBe("open");
  });

  it("orders incidents newest first for the incident console", () => {
    const model = buildDashboardModel(createDemoReplayEvents());

    expect(model.incidents.map((incident) => incident.id)).toEqual([
      "incident-billing-merge",
      "incident-cache-guardrail",
      "incident-duplicate-auth",
    ]);
  });

  it("tracks agent coding and reassignment state", () => {
    const model = buildDashboardModel(createDemoReplayEvents());
    const agent01 = model.agents.find((agent) => agent.id === "agent-01");
    const agent02 = model.agents.find((agent) => agent.id === "agent-02");

    expect(agent01?.status).toBe("coding");
    expect(agent02?.status).toBe("reassigned");
    expect(agent02?.taskTitle).toContain("Search filters");
    expect(agent02?.filePath).toContain("search");
    expect(agent02?.filePath).not.toContain("auth");
  });

  it("sorts shuffled replay events by timestamp", () => {
    const events = createDemoReplayEvents();
    const shuffledEvents = [...events].reverse();
    const model = buildDashboardModel(shuffledEvents);

    expect(model.timeline.map((event) => event.id)).toEqual(
      events.map((event) => event.id),
    );
  });

  it("uses event data for non-agent-02 duplicate and reassignment handling", () => {
    const events: TimelineEvent[] = [
      {
        id: "generic-001",
        timestamp: "2026-05-16T17:00:00.000Z",
        kind: "agent_started",
        title: "Agent 07 started profile work",
        description: "Agent 07 began profile settings work.",
        agent: {
          id: "agent-07",
          name: "Agent 07",
          status: "coding",
          taskTitle: "Profile settings panel",
        },
      },
      {
        id: "generic-002",
        timestamp: "2026-05-16T17:00:10.000Z",
        kind: "agent_started",
        title: "Agent 08 started profile work",
        description: "Agent 08 began overlapping profile settings work.",
        agent: {
          id: "agent-08",
          name: "Agent 08",
          status: "coding",
          taskTitle: "Profile notification preferences",
          filePath: "src/profile/preferences.ts",
        },
      },
      {
        id: "generic-003",
        timestamp: "2026-05-16T17:01:00.000Z",
        kind: "duplicate_detected",
        title: "Duplicate profile work detected",
        description: "Agent 08 should pause until reassigned.",
        agentIds: ["agent-07", "agent-08"],
        blockedAgentIds: ["agent-08"],
        incident: {
          id: "incident-profile-duplicate",
          type: "duplicate_work",
          status: "open",
          title: "Duplicate profile work",
          summary: "Two agents are changing profile preferences.",
          agentIds: ["agent-07", "agent-08"],
          suggestedTask: "Settings import flow",
          createdAt: "2026-05-16T17:01:00.000Z",
        },
      },
      {
        id: "generic-004",
        timestamp: "2026-05-16T17:02:00.000Z",
        kind: "agent_reassigned",
        title: "Agent 08 reassigned",
        description: "Agent 08 moved to settings import flow.",
        agentId: "agent-08",
        taskTitle: "Settings import flow",
      },
    ];

    const model = buildDashboardModel(events);
    const agent07 = model.agents.find((agent) => agent.id === "agent-07");
    const agent08 = model.agents.find((agent) => agent.id === "agent-08");

    expect(agent07?.status).toBe("coding");
    expect(agent08?.status).toBe("reassigned");
    expect(agent08?.taskTitle).toBe("Settings import flow");
    expect(agent08?.filePath).toBeUndefined();
    expect(model.metrics.activeAgents).toBe(2);
    expect(model.metrics.reassignedAgents).toBe(1);
  });
});
