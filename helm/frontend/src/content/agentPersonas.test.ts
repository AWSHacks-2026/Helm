import { describe, expect, it } from "vitest";

import {
  formatAgentIdList,
  formatAgentName,
  humanizeAgentText,
} from "./agentPersonas";

describe("agentPersonas", () => {
  it("maps demo agent ids to first names", () => {
    expect(formatAgentName("agent_a")).toBe("Ravi");
    expect(formatAgentName("agent_b")).toBe("Priya");
  });

  it("humanizes timeline copy", () => {
    expect(humanizeAgentText("agent_b overlaps agent_a on auth.py")).toBe(
      "Priya overlaps Ravi on auth.py",
    );
  });

  it("formats agent lists for incidents", () => {
    expect(formatAgentIdList(["agent_a", "agent_b"])).toBe("Ravi, Priya");
  });
});
