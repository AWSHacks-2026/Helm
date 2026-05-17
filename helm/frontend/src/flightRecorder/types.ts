import type { AgentStatus } from "../orchestration/types";

export type TraceFileStatus = "clean" | "editing" | "conflict" | "merged" | "blocked";

export interface TraceFileState {
  path: string;
  status: TraceFileStatus;
  snippet: string;
  highlight?: { start: number; end: number };
}

export interface TraceAgentState {
  id: string;
  status: AgentStatus;
  taskTitle: string;
  filePath: string;
}

export interface TraceHelmState {
  active: boolean;
  action?: "dedup" | "guardrail" | "merge" | "gate" | "reassign";
  detail?: string;
}

export type TraceEdgeKind =
  | "idle"
  | "coding"
  | "blocked"
  | "reassigned"
  | "conflicted"
  | "complete"
  | "dedup"
  | "guardrail"
  | "merge";

export interface TraceEdge {
  from: "helm";
  to: string;
  kind: TraceEdgeKind;
  label?: string;
}

export interface TraceFrame {
  id: string;
  atMs: number;
  title: string;
  narration: string;
  agents: TraceAgentState[];
  helm: TraceHelmState;
  edges: TraceEdge[];
  files: TraceFileState[];
  sourceEventId?: string;
}

export interface FlightTraceMeta {
  path_mode?: string;
  source_log?: string;
  source_matrix?: string;
  phase_count?: number;
  baseline_cost?: string;
  helm_cost?: string;
  cost_savings_pct?: number;
  token_savings_pct?: number;
  time_savings_pct?: number;
  baseline_tokens?: number;
  helm_tokens?: number;
  gate_skipped?: boolean;
  helm_gate_skipped?: boolean;
  guardrails_blocked?: number;
  dedup_calls?: number;
  helm_dedup_calls?: number;
  generated_at?: string;
}

export interface FlightTrace {
  id: string;
  label: string;
  description: string;
  frames: TraceFrame[];
  meta?: FlightTraceMeta;
}

export interface TraceScenario {
  id: string;
  label: string;
  description: string;
  load: () => FlightTrace | Promise<FlightTrace>;
}
