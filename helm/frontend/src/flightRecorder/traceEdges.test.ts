import { describe, expect, it } from "vitest";

import { buildTraceEdges } from "./traceEdges";

describe("buildTraceEdges", () => {
  it("colors helm to agent edges by status", () => {
    const edges = buildTraceEdges(
      [
        { id: "agent_a", status: "coding", taskTitle: "a", filePath: "f" },
        { id: "agent_b", status: "blocked", taskTitle: "b", filePath: "f" },
      ],
      { active: true, action: "guardrail", detail: "blocked write" },
    );
    expect(edges.find((e) => e.to === "agent_b")?.kind).toBe("guardrail");
    expect(edges.find((e) => e.to === "agent_a")?.kind).toBe("coding");
  });
});
