import { describe, expect, it } from "vitest";

import { PROBLEM_PAGE, SOLUTION_PAGE } from "./presentationPages";

describe("presentation page content", () => {
  it("keeps the problem statement focused on agent thrashing and customer impact", () => {
    const text = JSON.stringify(PROBLEM_PAGE).toLowerCase();

    expect(PROBLEM_PAGE.title).toContain("Agent fleets");
    expect(text).toContain("thrashing");
    expect(text).toContain("duplicate");
    expect(text).toContain("token");
    expect(text).toContain("cost");
    expect(text).toContain("review");
    expect(text).toContain("same repo");
  });

  it("keeps the solution page simple while preserving the concurrency analogy", () => {
    const text = JSON.stringify(SOLUTION_PAGE).toLowerCase();

    expect(SOLUTION_PAGE.title).toContain("coordinator");
    expect(text).toContain("dining philosophers");
    expect(text).toContain("threads");
    expect(text).toContain("helm");
    expect(text).toContain("intent");
    expect(text).toContain("guardrails");
  });
});
