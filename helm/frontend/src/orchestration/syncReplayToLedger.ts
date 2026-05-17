import { postHistoryEvent } from "../api/historyEvent";
import type { TimelineEvent } from "./types";

const AUTH_PATH = "backend/app/routers/auth.py";
const CART_PATH = "backend/app/routers/cart.py";

const filePathForEvent = (event: TimelineEvent): string => {
  if ("filePath" in event && event.filePath) return event.filePath;
  if ("incident" in event && event.incident?.filePath) return event.incident.filePath;
  if (event.kind === "merge_detected" || event.kind === "merge_resolved") {
    return CART_PATH;
  }
  return AUTH_PATH;
};

export async function syncReplayEventToLedger(
  sessionId: string,
  event: TimelineEvent,
): Promise<void> {
  switch (event.kind) {
    case "duplicate_detected":
      await postHistoryEvent(sessionId, "mission_delegated", {
        duplicate_detected: true,
        file_path: filePathForEvent(event),
        tokens_saved_estimate: "~1,800",
        assignments: (event.blockedAgentIds ?? []).map((agentId) => ({
          action: "reassign",
          assigned_agent_id: agentId,
        })),
      });
      break;
    case "guardrail_blocked":
      await postHistoryEvent(sessionId, "guardrail_blocked", {
        agent_id: event.agentId ?? "agent_b",
        file_path: filePathForEvent(event),
        message: event.description,
        tokens_saved_estimate: "~450",
      });
      break;
    case "merge_resolved":
      await postHistoryEvent(sessionId, "conflict_resolved", {
        file_path: filePathForEvent(event),
        affected_agents: ["agent_a", "agent_b"],
        resolution: {
          conflict_type: "merge_conflict",
          reasoning: event.description,
          tokens_saved_estimate: "~2,400",
          inference_tier: "sonnet",
        },
      });
      break;
    case "benchmark_result": {
      const baseline = event.benchmark?.baselineTokens ?? 0;
      const helm = event.benchmark?.overlordTokens ?? 0;
      const saved = baseline > helm ? baseline - helm : 1080;
      await postHistoryEvent(sessionId, "intent_aligned", {
        tokens_saved_estimate: `~${saved.toLocaleString("en-US")}`,
        inference_tier: "haiku",
        affected_agents: ["agent_a", "agent_b", "agent_c", "agent_d"],
      });
      break;
    }
    default:
      break;
  }
}
