import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { LandingPage } from "./LandingPage";

describe("LandingPage", () => {
  it("includes hero course-lines illustration", () => {
    const html = renderToStaticMarkup(
      <LandingPage
        sessionId="demo"
        onSessionIdChange={() => undefined}
        onStartReplay={() => undefined}
        onStartJudgeDemo={() => undefined}
      />,
    );
    expect(html).toContain("landing-hero-art");
    expect(html).toContain("Agent paths converging");
    expect(html).toContain("Build with Gratitude");
  });
});
