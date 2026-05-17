import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ProblemStatementPage } from "./ProblemStatementPage";
import { SolutionPage } from "./SolutionPage";
import { TechnicalWorkflowPage } from "./TechnicalWorkflowPage";

describe("presentation pages", () => {
  it("renders the problem statement page with the required pitch points", () => {
    const html = renderToStaticMarkup(<ProblemStatementPage />);

    expect(html).toContain("Problem Statement");
    expect(html).toContain("Agent fleets thrash");
    expect(html).toContain("Duplicate tasks");
    expect(html).toContain("Token burn");
    expect(html).toContain("Human drag");
    expect(html).toContain("presentation-page--problem");
  });

  it("renders the solution page with the coordination analogy", () => {
    const html = renderToStaticMarkup(<SolutionPage />);

    expect(html).toContain("Our Solution");
    expect(html).toContain("Helm is the coordination layer");
    expect(html).toContain("dining philosophers");
    expect(html).toContain("Agents");
    expect(html).toContain("Helm");
    expect(html).toContain("Safe parallel work");
    expect(html).toContain("presentation-page--solution");
    expect(html).toContain("Research model: worst-case thrash vs Helm");
    expect(html).toContain("Agents vs Tokens Consumed");
    expect(html).toContain("Agents vs Runtime");
    expect(html).toContain("worst-case line");
    expect(html).toContain("exponential growth");
    expect(html).toContain("linear growth");
  });

  it("renders the technical workflow page with AWS and Bedrock architecture", () => {
    const html = renderToStaticMarkup(<TechnicalWorkflowPage />);

    expect(html).toContain("Technical Workflow");
    expect(html).toContain("How Helm coordinates agent fleets on AWS");
    expect(html).toContain("Helm / MergeAI system architecture");
    expect(html).toContain("POST /intents");
    expect(html).toContain("POST /missions/delegate");
    expect(html).toContain("Contention gate");
    expect(html).toContain("AgentCore Memory");
    expect(html).toContain("AgentCore Policy");
    expect(html).toContain("AgentCore Runtime");
    expect(html).toContain("Claude Haiku 4.5");
    expect(html).toContain("Claude Sonnet 4.6");
    expect(html).toContain("HELM_MOCK_BEDROCK");
    expect(html).toContain("presentation-page--technical");
    expect(html).not.toContain("architecture-connector");
  });
});
