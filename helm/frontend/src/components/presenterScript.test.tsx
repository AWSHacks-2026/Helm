import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PresenterScript } from "./PresenterScript";

describe("PresenterScript", () => {
  it("lists four acts from demo prep", () => {
    const html = renderToStaticMarkup(<PresenterScript />);
    expect(html).toContain("Act 1");
    expect(html).toContain("dedup Bedrock calls");
    expect(html).toContain("guardrail");
  });
});
