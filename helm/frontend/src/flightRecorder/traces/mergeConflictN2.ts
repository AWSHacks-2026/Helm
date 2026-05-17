import { createMergeConflictReplayEvents } from "../../orchestration/mergeConflictReplay";
import { buildTraceFrames, type TraceSnippetMap } from "../buildTraceFrames";
import type { FlightTrace } from "../types";

const CART_PATH = "backend/app/routers/cart.py";

export const MERGE_N2_SNIPPETS: TraceSnippetMap = {
  clean: "cart_clean",
  edit_a: "cart_agent_a_edit",
  edit_b: "cart_agent_b_edit",
  conflict: "cart_conflict",
  merged: "cart_merged",
  blocked: "cart_conflict",
};

export function loadMergeN2Trace(): FlightTrace {
  return {
    id: "merge_n2",
    label: "N=2 · Merge conflict (cart.py)",
    description:
      "Two agents collide on checkout_total — Helm detects conflict markers and merges with Sonnet arbitration.",
    frames: buildTraceFrames(createMergeConflictReplayEvents(), {
      primaryFile: CART_PATH,
      agentIds: ["agent_a", "agent_b"],
      snippets: MERGE_N2_SNIPPETS,
    }),
  };
}
