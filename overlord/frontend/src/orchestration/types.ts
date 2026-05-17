export type DashboardMode = "replay" | "live";

export type AgentStatus =
  | "idle"
  | "coding"
  | "blocked"
  | "conflicted"
  | "reassigned"
  | "complete";

export type IncidentType =
  | "merge_conflict"
  | "intent_conflict"
  | "guardrail_block"
  | "duplicate_work";

export type IncidentStatus =
  | "open"
  | "resolved"
  | "blocked"
  | "approved"
  | "rejected";

export type TimelineKind =
  | "agent_started"
  | "intent_declared"
  | "guardrail_blocked"
  | "merge_detected"
  | "merge_resolved"
  | "duplicate_detected"
  | "agent_reassigned"
  | "benchmark_result"
  | "human_review";

export type ProjectHealth = "clean" | "needs_review" | "blocked";

export interface AgentTask {
  id: string;
  title: string;
  domain: string;
}

export interface AgentState {
  id: string;
  name: string;
  status: AgentStatus;
  taskTitle: string;
  filePath?: string;
}

export interface IncidentState {
  id: string;
  type: IncidentType;
  status: IncidentStatus;
  title: string;
  summary: string;
  filePath?: string;
  agentIds: string[];
  reasoning?: string;
  resolvedCode?: string;
  suggestedTask?: string;
  createdAt: string;
}

export interface BenchmarkResult {
  tokenSavingsLabel: string;
  baselineTokens: number;
  overlordTokens: number;
}

export interface TimelineEventBase {
  id: string;
  timestamp: string;
  title: string;
  description: string;
}

export interface AgentStartedEvent extends TimelineEventBase {
  kind: "agent_started";
  agent: AgentState;
}

export interface IntentDeclaredEvent extends TimelineEventBase {
  kind: "intent_declared";
  agentId: string;
  taskTitle: string;
  filePath?: string;
}

export interface GuardrailBlockedEvent extends TimelineEventBase {
  kind: "guardrail_blocked";
  agentId: string;
  incident?: IncidentState;
}

export interface MergeDetectedEvent extends TimelineEventBase {
  kind: "merge_detected";
  agentId: string;
  incident?: IncidentState;
}

export interface MergeResolvedEvent extends TimelineEventBase {
  kind: "merge_resolved";
  agentId?: string;
  incidentId?: string;
}

export interface DuplicateDetectedEvent extends TimelineEventBase {
  kind: "duplicate_detected";
  agentIds: string[];
  blockedAgentIds?: string[];
  incident?: IncidentState;
}

export interface AgentReassignedEvent extends TimelineEventBase {
  kind: "agent_reassigned";
  agentId: string;
  taskTitle: string;
  filePath?: string;
}

export interface BenchmarkResultEvent extends TimelineEventBase {
  kind: "benchmark_result";
  benchmark: BenchmarkResult;
}

export interface HumanReviewEvent extends TimelineEventBase {
  kind: "human_review";
  agentId?: string;
  incidentId?: string;
}

export type TimelineEvent =
  | AgentStartedEvent
  | IntentDeclaredEvent
  | GuardrailBlockedEvent
  | MergeDetectedEvent
  | MergeResolvedEvent
  | DuplicateDetectedEvent
  | AgentReassignedEvent
  | BenchmarkResultEvent
  | HumanReviewEvent;

export interface DashboardMetrics {
  totalAgents: number;
  activeAgents: number;
  blockedAgents: number;
  reassignedAgents: number;
  completedAgents: number;
  openIncidents: number;
  overlordActions: number;
  tokenSavingsLabel: string;
  projectHealth: ProjectHealth;
}

export interface DashboardModel {
  mode: DashboardMode;
  title: string;
  subtitle: string;
  agents: AgentState[];
  incidents: IncidentState[];
  timeline: TimelineEvent[];
  metrics: DashboardMetrics;
}
