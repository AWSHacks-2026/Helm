import { Children, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ControlTower } from "./ControlTower";
import { IncidentConsole } from "./IncidentConsole";
import { LandingPage } from "./LandingPage";
import type { DashboardModel } from "../orchestration/types";

const reactState = vi.hoisted(() => ({
  selectedFilter: "all",
  setSelectedFilter: vi.fn(),
}));

vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();

  return {
    ...actual,
    useState: vi.fn((initialValue: string) => [
      reactState.selectedFilter || initialValue,
      reactState.setSelectedFilter,
    ]),
  };
});

const model: DashboardModel = {
  mode: "replay",
  title: "Helm Control Tower",
  subtitle: "Replay coordination across the fleet.",
  agents: [
    {
      id: "agent-01",
      name: "Agent 01",
      status: "coding",
      taskTitle: "Checkout totals",
      filePath: "src/checkout/totals.ts",
    },
    {
      id: "agent-02",
      name: "Agent 02",
      status: "blocked",
      taskTitle: "Payment guardrail",
    },
  ],
  incidents: [
    {
      id: "incident-new",
      type: "merge_conflict",
      status: "open",
      title: "Checkout merge conflict",
      summary: "Two agents edited the same checkout helper.",
      filePath: "src/checkout/totals.ts",
      agentIds: ["agent-01", "agent-02"],
      reasoning: "Keep the typed total calculation and preserve guardrail checks.",
      suggestedTask: "Move Agent 02 to invoice export.",
      resolvedCode: "export const total = calculateTotal(cart);",
      createdAt: "not-a-real-timestamp",
    },
    {
      id: "incident-old",
      type: "duplicate_work",
      status: "resolved",
      title: "Duplicate auth work",
      summary: "Two agents started session storage.",
      agentIds: ["agent-03"],
      createdAt: "2026-05-16T16:00:00.000Z",
    },
  ],
  timeline: [
    {
      id: "timeline-01",
      kind: "merge_detected",
      timestamp: "not-a-real-timestamp",
      title: "Merge detected",
      description: "Helm found a checkout conflict.",
      agentId: "agent-01",
      incident: {
        id: "incident-new",
        type: "merge_conflict",
        status: "open",
        title: "Checkout merge conflict",
        summary: "Two agents edited the same checkout helper.",
        filePath: "src/checkout/totals.ts",
        agentIds: ["agent-01", "agent-02"],
        createdAt: "not-a-real-timestamp",
      },
    },
  ],
  metrics: {
    totalAgents: 2,
    activeAgents: 1,
    blockedAgents: 1,
    reassignedAgents: 0,
    completedAgents: 0,
    openIncidents: 1,
    overlordActions: 3,
    tokenSavingsLabel: "42%",
    projectHealth: "needs_review",
  },
};

const emptyModel: DashboardModel = {
  ...model,
  agents: [],
  incidents: [],
  timeline: [],
  metrics: {
    ...model.metrics,
    totalAgents: 0,
    activeAgents: 0,
    blockedAgents: 0,
    openIncidents: 0,
    overlordActions: 0,
    tokenSavingsLabel: "0%",
    projectHealth: "clean",
  },
};

type PropsWithChildren = {
  children?: ReactNode;
};

type ButtonProps = {
  onClick?: () => void;
};

type InputProps = {
  onChange?: (event: { target: { value: string } }) => void;
};

const walkElements = (node: ReactNode): ReactElement[] => {
  const elements: ReactElement[] = [];

  Children.forEach(node, (child) => {
    if (!isValidElement(child)) {
      return;
    }

    elements.push(child);
    elements.push(...walkElements((child.props as PropsWithChildren).children));
  });

  return elements;
};

const textContent = (node: ReactNode): string => {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }

  if (!isValidElement(node)) {
    return "";
  }

  return Children.toArray((node.props as PropsWithChildren).children)
    .map(textContent)
    .join("");
};

describe("dashboard components", () => {
  beforeEach(() => {
    reactState.selectedFilter = "all";
    reactState.setSelectedFilter.mockClear();
  });

  it("renders the landing page session controls and proof strip", () => {
    const html = renderToStaticMarkup(
      <LandingPage
        sessionId="team-demo"
        onSessionIdChange={() => undefined}
        onStartReplay={() => undefined}
        onOpenLiveSession={() => undefined}
      />,
    );

    expect(html).toContain("landing-page");
    expect(html).toContain("Watch Demo");
    expect(html).toContain("Open Live Session");
    expect(html).toContain("value=\"team-demo\"");
    expect(html).toContain("Merge conflicts");
    expect(html).toContain("Guardrails");
    expect(html).toContain("Dedup");
  });

  it("wires landing page session and action callbacks", () => {
    const onSessionIdChange = vi.fn();
    const onStartReplay = vi.fn();
    const onOpenLiveSession = vi.fn();
    const root = LandingPage({
      sessionId: "team-demo",
      onSessionIdChange,
      onStartReplay,
      onOpenLiveSession,
    });
    const elements = walkElements(root);
    const buttons = elements.filter((element) => element.type === "button");
    const input = elements.find((element) => element.type === "input");

    (buttons[0].props as ButtonProps).onClick?.();
    (buttons[1].props as ButtonProps).onClick?.();
    (input?.props as InputProps).onChange?.({
      target: { value: "live-team-session" },
    });

    expect(onStartReplay).toHaveBeenCalledTimes(1);
    expect(onOpenLiveSession).toHaveBeenCalledTimes(1);
    expect(onSessionIdChange).toHaveBeenCalledWith("live-team-session");
  });

  it("renders control tower metrics, fleet, timeline, incidents, and raw invalid timestamps", () => {
    const html = renderToStaticMarkup(
      <ControlTower
        model={model}
        connectionLabel="Replay connected"
        onSelectIncident={() => undefined}
      />,
    );

    expect(html).toContain("control-tower");
    expect(html).toContain("Replay connected");
    expect(html).toContain("Active agents");
    expect(html).toContain("Helm actions");
    expect(html).toContain("Token savings");
    expect(html).toContain("Project health");
    expect(html).toContain("Agent 01");
    expect(html).toContain("status-coding");
    expect(html).toContain("Merge detected");
    expect(html).toContain("not-a-real-timestamp");
    expect(html).toContain("Checkout merge conflict");
  });

  it("wires control tower incident selection and timeline datetime attributes", () => {
    const onSelectIncident = vi.fn();
    const root = ControlTower({ model, onSelectIncident });
    const elements = walkElements(root);
    const incidentButton = elements.find(
      (element) =>
        element.type === "button" &&
        textContent(element).includes("Checkout merge conflict"),
    );
    const timelineTime = elements.find((element) => element.type === "time");

    (incidentButton?.props as ButtonProps).onClick?.();

    expect(onSelectIncident).toHaveBeenCalledWith("incident-new");
    expect(timelineTime?.props).toMatchObject({
      dateTime: "not-a-real-timestamp",
      children: "not-a-real-timestamp",
    });
  });

  it("renders useful empty states in the control tower", () => {
    const html = renderToStaticMarkup(
      <ControlTower model={emptyModel} onSelectIncident={() => undefined} />,
    );

    expect(html.match(/empty-state/g)?.length).toBeGreaterThanOrEqual(3);
    expect(html).toContain("No agents are active yet");
    expect(html).toContain("No timeline events yet");
    expect(html).toContain("No incidents detected");
  });

  it("renders incident filters, queue order, and fallback detail content", () => {
    const html = renderToStaticMarkup(
      <IncidentConsole
        model={model}
        selectedIncidentId="missing-incident"
        onSelectIncident={() => undefined}
      />,
    );

    expect(html).toContain("incident-console");
    expect(html).toContain("Merge conflict");
    expect(html).toContain("Intent conflict");
    expect(html).toContain("Guardrail block");
    expect(html).toContain("Duplicate work");
    expect(html.indexOf("Checkout merge conflict")).toBeLessThan(
      html.indexOf("Duplicate auth work"),
    );
    expect(html).toContain("Keep the typed total calculation");
    expect(html).toContain("Move Agent 02 to invoice export.");
    expect(html).toContain("export const total = calculateTotal(cart);");
  });

  it("filters the incident queue and falls back to the first matching detail", () => {
    reactState.selectedFilter = "merge_conflict";

    const html = renderToStaticMarkup(
      <IncidentConsole
        model={model}
        selectedIncidentId="incident-old"
        onSelectIncident={() => undefined}
      />,
    );

    expect(html).toContain("Checkout merge conflict");
    expect(html).not.toContain("Duplicate auth work");
    expect(html).toContain("Keep the typed total calculation");
  });

  it("renders filter controls as buttons and wires filter state", () => {
    const root = IncidentConsole({
      model,
      selectedIncidentId: null,
      onSelectIncident: () => undefined,
    });
    const duplicateFilterButton = walkElements(root).find(
      (element) =>
        element.type === "button" && textContent(element) === "Duplicate work",
    );

    (duplicateFilterButton?.props as ButtonProps).onClick?.();

    expect(reactState.setSelectedFilter).toHaveBeenCalledWith("duplicate_work");
  });

  it("renders an empty state when the selected filter has no incidents", () => {
    reactState.selectedFilter = "guardrail_block";

    const html = renderToStaticMarkup(
      <IncidentConsole
        model={model}
        selectedIncidentId={null}
        onSelectIncident={() => undefined}
      />,
    );

    expect(html).toContain("No guardrail block incidents in the queue");
    expect(html).not.toContain("Checkout merge conflict");
    expect(html).not.toContain("Duplicate auth work");
  });

  it("renders an incident console empty state", () => {
    const html = renderToStaticMarkup(
      <IncidentConsole
        model={emptyModel}
        selectedIncidentId={null}
        onSelectIncident={() => undefined}
      />,
    );

    expect(html).toContain("empty-state");
    expect(html).toContain("No incidents in the queue");
  });
});
