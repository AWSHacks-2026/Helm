import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { BenchmarkProof } from "./BenchmarkProof";
import { LegacyLabPanel } from "./LegacyLabPanel";

vi.mock("../hooks/usePresenterMode", () => ({
  readPresenterMode: () => false,
}));

describe("BenchmarkProof", () => {
  it("renders benchmark results with charts and pillar headlines", () => {
    const html = renderToStaticMarkup(<BenchmarkProof />);

    expect(html).toContain("Benchmark results");
    expect(html).toContain("/demo-charts/00_dashboard.png");
    expect(html).toContain("N=8: +18% cost");
    expect(html).toContain("Run guardrail check");
    expect(html).not.toContain("Run live token benchmark");
    expect(html).not.toContain("Presenter script");
  });
});

describe("LegacyLabPanel", () => {
  it("renders existing lab components in the legacy grid", () => {
    const html = renderToStaticMarkup(<LegacyLabPanel />);

    expect(html).toContain("Developer Labs");
    expect(html).toContain("Existing demo tools");
    expect(html).toContain("legacy-grid");
  });
});
