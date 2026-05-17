import { describe, expect, it } from "vitest";

import { PROBLEM_PAGE, SOLUTION_PAGE, TECHNICAL_WORKFLOW_PAGE } from "./presentationPages";

describe("presentation page content", () => {
  it("keeps the problem statement focused on agent thrashing and customer impact", () => {
    const text = JSON.stringify(PROBLEM_PAGE).toLowerCase();

    expect(PROBLEM_PAGE.title).toContain("Agent fleets");
    expect(text).toContain("thrashing");
    expect(text).toContain("duplicate");
    expect(text).toContain("token");
    expect(text).toContain("cost");
    expect(text).toContain("review");
    expect(text).toContain("repo");
  });

  it("keeps the solution page simple while preserving the concurrency analogy", () => {
    const text = JSON.stringify(SOLUTION_PAGE).toLowerCase();

    expect(SOLUTION_PAGE.title).toContain("coordination layer");
    expect(text).toContain("dining philosophers");
    expect(text).toContain("threads");
    expect(text).toContain("helm");
    expect(text).toContain("intent");
    expect(text).toContain("guardrails");
  });

  it("keeps the technical workflow page focused on AWS, Bedrock, and source-backed flow", () => {
    const text = JSON.stringify(TECHNICAL_WORKFLOW_PAGE).toLowerCase();

    expect(TECHNICAL_WORKFLOW_PAGE.title).toContain("How Helm coordinates");
    expect(text).toContain("react 19");
    expect(text).toContain("fastapi");
    expect(text).toContain("agentcore memory");
    expect(text).toContain("agentcore policy");
    expect(text).toContain("agentcore runtime");
    expect(text).toContain("haiku 4.5");
    expect(text).toContain("sonnet 4.6");
    expect(text).toContain("contention gate");
    expect(text).toContain("guardrails");
    expect(text).toContain("helm_mock_bedrock");
  });
});
