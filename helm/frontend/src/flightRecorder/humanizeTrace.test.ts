import { describe, expect, it } from "vitest";

import { humanizeTrace } from "./humanizeTrace";
import type { FlightTrace } from "./types";

const trace: FlightTrace = {
  id: "t",
  label: "Test",
  description: "agent_a and agent_b collide",
  frames: [
    {
      id: "f0",
      atMs: 0,
      title: "agent_a started",
      narration: "agent_b blocked",
      agents: [
        { id: "agent_a", status: "coding", taskTitle: "t", filePath: "f" },
        { id: "agent_b", status: "idle", taskTitle: "—", filePath: "f" },
      ],
      helm: { active: true, action: "dedup", detail: "reassign agent_b" },
      edges: [],
      files: [],
    },
  ],
};

describe("humanizeTrace", () => {
  it("replaces agent ids in trace copy", () => {
    const result = humanizeTrace(trace);
    expect(result.description).toBe("Ravi and Priya collide");
    expect(result.frames[0].title).toBe("Ravi started");
    expect(result.frames[0].narration).toBe("Priya blocked");
    expect(result.frames[0].helm.detail).toBe("reassign Priya");
  });
});
