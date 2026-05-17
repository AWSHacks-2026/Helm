import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PillarHeadlineCards } from "./PillarHeadlineCards";

describe("PillarHeadlineCards", () => {
  it("renders all four pillar headlines", () => {
    const html = renderToStaticMarkup(<PillarHeadlineCards />);
    expect(html).toContain("Contention gate");
    expect(html).toContain("ShopFix auth.py");
    expect(html).toContain("+39% wall");
  });
});
