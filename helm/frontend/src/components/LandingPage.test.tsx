import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { LandingPage } from "./LandingPage";

describe("LandingPage", () => {
  it("renders hero copy without decorative illustration", () => {
    const html = renderToStaticMarkup(
      <LandingPage
        sessionId="demo"
        onSessionIdChange={() => undefined}
        onStartReplay={() => undefined}
        onStartJudgeDemo={() => undefined}
      />,
    );
    expect(html).not.toContain("landing-hero-art");
    expect(html).not.toContain("hero-course-lines");
    expect(html).toContain("hero-copy");
    expect(html).toContain("Build with Gratitude");
  });
});
