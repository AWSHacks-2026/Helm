import { describe, expect, it } from "vitest";

import { createMergeConflictReplayEvents } from "../orchestration/mergeConflictReplay";
import { buildTraceFrames } from "./buildTraceFrames";

const MERGE_SNIPPETS = {
  clean: "cart_clean",
  edit_a: "cart_agent_a_edit",
  edit_b: "cart_agent_b_edit",
  conflict: "cart_conflict",
  merged: "cart_merged",
  blocked: "cart_conflict",
} as const;

describe("buildTraceFrames", () => {
  it("produces increasing atMs and activates helm on merge resolution", () => {
    const frames = buildTraceFrames(createMergeConflictReplayEvents(), {
      primaryFile: "backend/app/routers/cart.py",
      agentIds: ["agent_a", "agent_b"],
      snippets: MERGE_SNIPPETS,
    });
    expect(frames.length).toBeGreaterThan(3);
    expect(frames[0].atMs).toBe(0);
    expect(
      frames.some((frame) => frame.helm.active && frame.helm.action === "merge"),
    ).toBe(true);
    const conflict = frames.find((frame) => frame.files[0]?.status === "conflict");
    expect(conflict).toBeDefined();
  });
});
