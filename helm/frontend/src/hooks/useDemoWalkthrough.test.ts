import { describe, expect, it } from "vitest";

import { JUDGE_WALKTHROUGH } from "../demoWalkthrough";

describe("JUDGE_WALKTHROUGH", () => {
  it("guides replay, incidents, gratitude, and proof", () => {
    expect(JUDGE_WALKTHROUGH).toHaveLength(4);
    expect(JUDGE_WALKTHROUGH[0].view).toBe("control");
    expect(JUDGE_WALKTHROUGH[1].selectIncidentType).toBe("duplicate_work");
    expect(JUDGE_WALKTHROUGH[2].view).toBe("gratitude");
    expect(JUDGE_WALKTHROUGH[3].view).toBe("proof");
    expect(JUDGE_WALKTHROUGH[2].id).toBe("gratitude");
  });
});
