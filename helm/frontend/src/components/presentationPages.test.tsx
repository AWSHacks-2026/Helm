import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ProblemStatementPage } from "./ProblemStatementPage";
import { SolutionPage } from "./SolutionPage";

describe("presentation pages", () => {
  it("renders the problem statement page with the required pitch points", () => {
    const html = renderToStaticMarkup(<ProblemStatementPage />);

    expect(html).toContain("Problem Statement");
    expect(html).toContain("Agent fleets are starting to thrash");
    expect(html).toContain("Duplicate tasks");
    expect(html).toContain("Token burn");
    expect(html).toContain("Human drag");
    expect(html).toContain("presentation-page--problem");
  });

  it("renders the solution page with the coordination analogy", () => {
    const html = renderToStaticMarkup(<SolutionPage />);

    expect(html).toContain("Our Solution");
    expect(html).toContain("Overlord is the coordinator");
    expect(html).toContain("dining philosophers");
    expect(html).toContain("Agents");
    expect(html).toContain("Helm");
    expect(html).toContain("Safe parallel work");
    expect(html).toContain("presentation-page--solution");
  });
});
