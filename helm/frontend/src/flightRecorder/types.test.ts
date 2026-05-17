import { describe, expect, it } from "vitest";

import type { FlightTrace, TraceFrame } from "./types";

describe("flightRecorder types", () => {
  it("allows a minimal flight trace fixture shape", () => {
    const trace: FlightTrace = {
      id: "contention_n2",
      label: "N=2 dedup on auth.py",
      description: "Two agents collide; Helm dedupes.",
      frames: [
        {
          id: "f0",
          atMs: 0,
          title: "Start",
          narration: "agent_a opens auth.py",
          agents: [
            {
              id: "agent_a",
              status: "coding",
              taskTitle: "TTL",
              filePath: "backend/app/routers/auth.py",
            },
            {
              id: "agent_b",
              status: "idle",
              taskTitle: "—",
              filePath: "backend/app/routers/auth.py",
            },
          ],
          helm: { active: false },
          edges: [
            { from: "helm", to: "agent_a", kind: "coding" },
            { from: "helm", to: "agent_b", kind: "idle" },
          ],
          files: [
            {
              path: "backend/app/routers/auth.py",
              status: "clean",
              snippet: "router = APIRouter()",
            },
          ],
        } satisfies TraceFrame,
      ],
    };
    expect(trace.frames).toHaveLength(1);
  });
});
