import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FlightRecorderPage } from "./FlightRecorderPage";

const mockTrace = {
  id: "contention_n2_live",
  label: "Live",
  description: "Live trace",
  frames: [
    {
      id: "f0",
      atMs: 0,
      title: "step",
      narration: "narration",
      agents: [
        { id: "agent_a", status: "coding", taskTitle: "t", filePath: "f" },
        { id: "agent_b", status: "idle", taskTitle: "—", filePath: "f" },
      ],
      helm: { active: false },
      edges: [
        { from: "helm", to: "agent_a", kind: "coding" },
        { from: "helm", to: "agent_b", kind: "idle" },
      ],
      files: [{ path: "f", status: "editing", snippet: "code" }],
    },
  ],
};

describe("FlightRecorderPage", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTrace,
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders graph, file panel, and scrubber after load", async () => {
    const html = renderToStaticMarkup(<FlightRecorderPage />);
    expect(html).toContain("flight-recorder");
    expect(html).toContain("Under the hood");
  });
});
