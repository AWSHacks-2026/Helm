import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import GratitudeLedgerPanel, { GratitudeLedgerEmpty } from "./GratitudeLedger";

vi.mock("./hooks/useConflictStream", () => ({
  useConflictStream: () => undefined,
}));

vi.mock("./api/gratitude", () => ({
  fetchGratitude: vi.fn().mockResolvedValue({
    intents_declared: 2,
    guardrails_blocked: 1,
    intents_aligned: 1,
    duplicates_avoided: 1,
    agents_yielded: 1,
    tokens_saved_display: "~1,200 tokens",
    haiku_calls: 3,
    sonnet_calls: 1,
    timeline: [],
  }),
}));

describe("GratitudeLedgerPanel", () => {
  it("renders mission story and session ledger shell", () => {
    const html = renderToStaticMarkup(
      <GratitudeLedgerPanel sessionId="mergeai-hackathon-demo" />,
    );

    expect(html).toContain("Build with Gratitude");
    expect(html).toContain("Overlord");
    expect(html).toMatch(/parents/i);
    expect(html).toContain("What we gave back this session");
    expect(html).toContain("Session ledger");
    expect(html).toContain("Paying it forward");
    expect(html).toContain("Intent coordination");
    expect(html).toContain("Fleet sessions across machines");
    expect(html).toContain("CI/CD guardrails");
    expect(html).not.toContain(">Intents<");
  });

  it("renders empty-state illustration markup", () => {
    const html = renderToStaticMarkup(<GratitudeLedgerEmpty />);
    expect(html).toContain("gratitude-empty-art");
    expect(html).toContain("Tokens and time returning");
  });
});
