import { describe, expect, it } from "vitest";

import type { FlightTrace } from "../flightRecorder/types";

const trace: FlightTrace = {
  id: "t",
  label: "t",
  description: "d",
  frames: [
    {
      id: "f0",
      atMs: 0,
      title: "a",
      narration: "a",
      agents: [],
      helm: { active: false },
      edges: [],
      files: [],
    },
    {
      id: "f1",
      atMs: 1000,
      title: "b",
      narration: "b",
      agents: [],
      helm: { active: true, action: "dedup" },
      edges: [],
      files: [],
    },
  ],
};

describe("useTracePlayback trace fixture", () => {
  it("exposes two frames for playback tests", () => {
    expect(trace.frames).toHaveLength(2);
    expect(trace.frames[1].helm.active).toBe(true);
  });
});
