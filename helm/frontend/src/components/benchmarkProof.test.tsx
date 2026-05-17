import { Children, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { compareMergeScenario } from "../api/mergeLab";
import { runLiveBenchmark } from "../api/liveBenchmark";
import { BenchmarkProof } from "./BenchmarkProof";
import { LegacyLabPanel } from "./LegacyLabPanel";

const reactState = vi.hoisted(() => ({
  setState: vi.fn(),
}));

vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();

  return {
    ...actual,
    useState: vi.fn((initialValue: unknown) => [initialValue, reactState.setState]),
  };
});

vi.mock("../api/liveBenchmark", () => ({
  runLiveBenchmark: vi.fn().mockResolvedValue({
    scenario: "merge_conflict",
    mock_bedrock: true,
    seed_mode: "scenario",
    comparison: {
      baseline_tokens: 1000,
      helm_tokens: 400,
      token_savings_pct: 60,
      baseline_cost_usd: 0.01,
      helm_cost_usd: 0.004,
      cost_savings_pct: 60,
      baseline_cost_display: "$0.0100",
      helm_cost_display: "$0.0040",
      helm_beats_cost: true,
      baseline_score: 40,
      helm_score: 90,
      helm_beats_tokens: true,
      helm_beats_quality: true,
      baseline_passed: false,
      helm_passed: true,
    },
    baseline: { rounds: 1, final_code: "baseline" },
    helm: { rounds: 1, final_code: "helm" },
  }),
}));

vi.mock("../api/mergeLab", () => ({
  compareMergeScenario: vi.fn().mockResolvedValue({
    scenario: "merge_conflict",
    file_path: "src/cart.ts",
    mock_bedrock: true,
    agent_a: { intent: "A", code: "A" },
    agent_b: { intent: "B", code: "B" },
    results: [],
    summary: {
      helm_passed: true,
      helm_score: 95,
      best_naive_strategy: "pick_agent_a",
      best_naive_score: 65,
      helm_beats_naive: true,
      score_delta: 30,
    },
    mcp_hint: { tool: "merge", session_id: "demo", file_path: "src/cart.ts" },
  }),
}));

vi.mock("../MergeLab", () => ({
  default: () => <div>Merge lab mock</div>,
}));

vi.mock("../DemoLab", () => ({
  default: () => <div>Demo lab mock</div>,
}));

type PropsWithChildren = {
  children?: ReactNode;
};

type ButtonProps = {
  onClick?: () => void | Promise<void>;
};

const walkElements = (node: ReactNode): ReactElement[] => {
  const elements: ReactElement[] = [];

  Children.forEach(node, (child) => {
    if (!isValidElement(child)) {
      return;
    }

    elements.push(child);
    elements.push(...walkElements((child.props as PropsWithChildren).children));
  });

  return elements;
};

const textContent = (node: ReactNode): string => {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }

  if (!isValidElement(node)) {
    return "";
  }

  return Children.toArray((node.props as PropsWithChildren).children)
    .map(textContent)
    .join("");
};

describe("BenchmarkProof", () => {
  it("renders benchmark proof copy and static commerce caveat", () => {
    const html = renderToStaticMarkup(<BenchmarkProof />);

    expect(html).toContain("Benchmark Proof");
    expect(html).toContain("With Helm vs without Helm");
    expect(html).toContain("Run live token benchmark");
    expect(html).toContain("Run merge comparison");
    expect(html).toContain("helm/demo/generated/static-commerce-rich/");
    expect(html).toContain("backend manifest route");
    expect(html).toContain("not live frontend results");
  });

  it("runs proof API calls from button handlers with the merge conflict scenario", async () => {
    const root = BenchmarkProof();
    const buttons = walkElements(root).filter((element) => element.type === "button");

    expect(runLiveBenchmark).not.toHaveBeenCalled();
    expect(compareMergeScenario).not.toHaveBeenCalled();

    await (buttons.find((button) => textContent(button).includes("token"))?.props as ButtonProps)
      .onClick?.();
    await (buttons.find((button) => textContent(button).includes("merge"))?.props as ButtonProps)
      .onClick?.();

    expect(runLiveBenchmark).toHaveBeenCalledWith("merge_conflict", "scenario");
    expect(compareMergeScenario).toHaveBeenCalledWith("merge_conflict");
  });
});

describe("LegacyLabPanel", () => {
  it("renders existing lab components in the legacy grid", () => {
    const html = renderToStaticMarkup(<LegacyLabPanel />);

    expect(html).toContain("Developer Labs");
    expect(html).toContain("Existing demo tools");
    expect(html).toContain("legacy-grid");
    expect(html).toContain("Merge lab mock");
    expect(html).toContain("Demo lab mock");
  });
});
