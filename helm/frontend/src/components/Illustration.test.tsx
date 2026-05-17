import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Illustration } from "./Illustration";
import { HelmMark } from "./HelmMark";

describe("Illustration", () => {
  it("renders hero and empty ledger assets", () => {
    const hero = renderToStaticMarkup(
      <Illustration name="hero-course-lines" alt="Hero" />,
    );
    const empty = renderToStaticMarkup(
      <Illustration name="empty-ledger" alt="Empty" />,
    );
    expect(hero).toContain("<img");
    expect(hero).toContain('role="img"');
    expect(empty).toContain("<img");
  });
});

describe("HelmMark", () => {
  it("renders accessible helm wheel mark", () => {
    const html = renderToStaticMarkup(<HelmMark />);
    expect(html).toContain("<svg");
    expect(html).toContain('aria-hidden="true"');
  });
});
