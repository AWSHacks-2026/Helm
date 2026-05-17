import { describe, expect, it } from "vitest";

import { readInitialView, readWalkthroughFlag } from "./readInitialView";

describe("readInitialView", () => {
  it("reads view from query string", () => {
    expect(readInitialView("?view=proof&presenter=1")).toBe("proof");
    expect(readInitialView("?view=problem")).toBe("problem");
    expect(readInitialView("?view=solution")).toBe("solution");
    expect(readInitialView("?view=technical")).toBe("technical");
    expect(readWalkthroughFlag("?walkthrough=1")).toBe(true);
  });
});
