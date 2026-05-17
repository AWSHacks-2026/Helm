import { describe, expect, it } from "vitest";

import { DEMO_PILLARS, pillarById } from "./demoHeadlines";

describe("demoHeadlines", () => {
  it("defines four pillars with positive savings where we claim wins", () => {
    expect(DEMO_PILLARS).toHaveLength(4);
    const contention = pillarById("contention");
    expect(contention?.costSavingsPct).toBeGreaterThan(0);
    expect(contention?.headline).toMatch(/N=8|8 agents/i);
  });
});
