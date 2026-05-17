import type { AgentState, IncidentState } from "./types";

export const demoAgent = (
  id: string,
  name: string,
  taskTitle: string,
  filePath: string,
): AgentState => ({
  id,
  name,
  status: "coding",
  taskTitle,
  filePath,
});

export const demoIncident = (
  id: string,
  type: IncidentState["type"],
  status: IncidentState["status"],
  title: string,
  summary: string,
  agentIds: string[],
  timestamp: string,
  options: {
    filePath?: string;
    reasoning?: string;
    resolvedCode?: string;
    suggestedTask?: string;
  } = {},
): IncidentState => ({
  id,
  type,
  status,
  title,
  summary,
  agentIds,
  createdAt: timestamp,
  ...options,
});
