import type {
  AgentState,
  DashboardMetrics,
  DashboardMode,
  DashboardModel,
  IncidentState,
  ProjectHealth,
  TimelineEvent,
  TimelineKind,
} from "./types";

const overlordActionKinds = new Set<TimelineKind>([
  "duplicate_detected",
  "agent_reassigned",
  "guardrail_blocked",
  "merge_detected",
  "merge_resolved",
]);

const sortByTimestamp = (events: TimelineEvent[]): TimelineEvent[] =>
  [...events].sort((left, right) => {
    const timestampComparison =
      Date.parse(left.timestamp) - Date.parse(right.timestamp);

    return timestampComparison === 0
      ? left.id.localeCompare(right.id)
      : timestampComparison;
  });

const cloneAgent = (agent: AgentState): AgentState => ({
  ...agent,
});

const cloneIncident = (incident: IncidentState): IncidentState => ({
  ...incident,
  agentIds: [...incident.agentIds],
});

const applyAgentUpdate = (
  agents: Map<string, AgentState>,
  agentId: string,
  update: (agent: AgentState) => AgentState,
): void => {
  const agent = agents.get(agentId);

  if (agent) {
    agents.set(agentId, update(agent));
  }
};

const calculateProjectHealth = (
  openIncidents: number,
  blockedAgents: number,
): ProjectHealth => {
  if (openIncidents > 0) {
    return "needs_review";
  }

  if (blockedAgents > 0) {
    return "blocked";
  }

  return "clean";
};

const buildMetrics = (
  agents: AgentState[],
  incidents: IncidentState[],
  timeline: TimelineEvent[],
): DashboardMetrics => {
  const blockedAgents = agents.filter((agent) => agent.status === "blocked").length;
  const reassignedAgents = agents.filter(
    (agent) => agent.status === "reassigned",
  ).length;
  const completedAgents = agents.filter((agent) => agent.status === "complete").length;
  const openIncidents = incidents.filter(
    (incident) => incident.status === "open",
  ).length;
  const activeAgents = agents.filter((agent) =>
    ["coding", "conflicted", "reassigned"].includes(agent.status),
  ).length;
  const tokenSavingsLabel =
    [...timeline]
      .reverse()
      .find((event) => event.kind === "benchmark_result")?.benchmark
      .tokenSavingsLabel ?? "42%";

  return {
    totalAgents: agents.length,
    activeAgents,
    blockedAgents,
    reassignedAgents,
    completedAgents,
    openIncidents,
    overlordActions: timeline.filter((event) =>
      overlordActionKinds.has(event.kind),
    ).length,
    tokenSavingsLabel,
    projectHealth: calculateProjectHealth(openIncidents, blockedAgents),
  };
};

export interface DashboardModelOptions {
  subtitle?: string;
  completeHint?: string;
}

export const buildDashboardModel = (
  events: TimelineEvent[],
  mode: DashboardMode = "replay",
  options: DashboardModelOptions = {},
): DashboardModel => {
  const timeline = sortByTimestamp(events);
  const agents = new Map<string, AgentState>();
  const incidents = new Map<string, IncidentState>();

  for (const event of timeline) {
    if (event.kind === "agent_started") {
      agents.set(event.agent.id, cloneAgent(event.agent));
    }

    if (event.kind === "intent_declared") {
      applyAgentUpdate(agents, event.agentId, (agent) => ({
        ...agent,
        status: "coding",
        taskTitle: event.taskTitle,
        filePath: event.filePath ?? agent.filePath,
      }));
    }

    if ("incident" in event && event.incident) {
      incidents.set(event.incident.id, cloneIncident(event.incident));
    }

    if (event.kind === "duplicate_detected") {
      const blockedAgentIds = event.blockedAgentIds ?? event.agentIds.slice(1);

      for (const agentId of blockedAgentIds) {
        applyAgentUpdate(agents, agentId, (agent) => ({
          ...agent,
          status: "blocked",
        }));
      }
    }

    if (event.kind === "agent_reassigned") {
      applyAgentUpdate(agents, event.agentId, (agent) => ({
        ...agent,
        status: "reassigned",
        taskTitle: event.taskTitle,
        filePath: event.filePath,
      }));

      for (const [incidentId, incident] of incidents) {
        if (
          incident.type === "duplicate_work" &&
          incident.status === "open" &&
          incident.agentIds.includes(event.agentId)
        ) {
          incidents.set(incidentId, { ...incident, status: "resolved" });
        }
      }
    }

    if (event.kind === "guardrail_blocked") {
      // Incident records the block; agent keeps its current task after Helm rejects the edit.
    }

    if (event.kind === "merge_detected") {
      applyAgentUpdate(agents, event.agentId, (agent) => ({
        ...agent,
        status: "conflicted",
      }));
    }

    if (event.kind === "merge_resolved") {
      if (event.incident) {
        incidents.set(event.incident.id, cloneIncident(event.incident));
      } else if (event.incidentId) {
        const existing = incidents.get(event.incidentId);
        if (existing) {
          incidents.set(event.incidentId, { ...existing, status: "resolved" });
        }
      }

      if (event.agentId) {
        applyAgentUpdate(agents, event.agentId, (agent) => ({
          ...agent,
          status: "coding",
        }));
      }
    }
  }

  const agentList = [...agents.values()].sort((left, right) =>
    left.id.localeCompare(right.id),
  );
  const incidentList = [...incidents.values()].sort((left, right) =>
    right.createdAt.localeCompare(left.createdAt),
  );

  const defaultSubtitle =
    mode === "replay"
      ? "ShopFix Etsy-lite · pick a scenario below or watch the guided replay."
      : "Live session — shared AgentCore memory and Bedrock coordination.";

  return {
    mode,
    title: "Helm Control Tower",
    subtitle: options.subtitle ?? defaultSubtitle,
    completeHint: options.completeHint,
    agents: agentList,
    incidents: incidentList,
    timeline,
    metrics: buildMetrics(agentList, incidentList, timeline),
  };
};
