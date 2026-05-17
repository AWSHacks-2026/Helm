import type { TraceAgentState, TraceEdge, TraceEdgeKind, TraceHelmState } from "./types";

export function buildTraceEdges(
  agents: TraceAgentState[],
  helm: TraceHelmState,
): TraceEdge[] {
  return agents.map((agent) => {
    let kind: TraceEdgeKind = "idle";
    const status = agent.status;

    if (helm.active) {
      const action = helm.action;
      if (action === "dedup" && status === "blocked") {
        kind = "dedup";
      } else if (action === "guardrail" && status === "blocked") {
        kind = "guardrail";
      } else if (action === "merge") {
        kind = status === "conflicted" ? "conflicted" : "merge";
      } else if (action === "reassign" || status === "reassigned") {
        kind = "reassigned";
      } else if (status === "coding") {
        kind = "coding";
      } else if (status === "blocked") {
        kind = "blocked";
      }
    } else if (status === "coding") {
      kind = "coding";
    } else if (status === "blocked") {
      kind = "blocked";
    } else if (status === "reassigned") {
      kind = "reassigned";
    } else if (status === "conflicted") {
      kind = "conflicted";
    } else if (status === "complete") {
      kind = "complete";
    }

    return {
      from: "helm",
      to: agent.id,
      kind,
      label: helm.active ? helm.detail : undefined,
    };
  });
}
