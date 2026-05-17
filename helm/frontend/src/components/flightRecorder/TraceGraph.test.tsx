import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { TraceFrame } from "../../flightRecorder/types";
import { TraceGraph } from "./TraceGraph";

const frame: TraceFrame = {
  id: "f0",
  atMs: 0,
  title: "t",
  narration: "n",
  agents: [
    { id: "agent_a", status: "coding", taskTitle: "a", filePath: "f" },
    { id: "agent_b", status: "blocked", taskTitle: "b", filePath: "f" },
  ],
  helm: { active: true, action: "guardrail" },
  edges: [
    { from: "helm", to: "agent_a", kind: "coding" },
    { from: "helm", to: "agent_b", kind: "guardrail" },
  ],
  files: [],
};

describe("TraceGraph", () => {
  it("renders svg edges and agent nodes", () => {
    const html = renderToStaticMarkup(<TraceGraph frame={frame} />);
    expect(html).toContain("trace-graph");
    expect(html).toContain("trace-edge-guardrail");
    expect(html).toContain("agent_a");
    expect(html).toContain("Helm");
  });
});
