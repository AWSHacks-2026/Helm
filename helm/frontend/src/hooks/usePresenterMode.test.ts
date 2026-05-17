import { describe, expect, it } from "vitest";

import { readPresenterMode } from "./usePresenterMode";

describe("readPresenterMode", () => {
  it("returns true when presenter query param is set", () => {
    expect(readPresenterMode("?presenter=1")).toBe(true);
  });

  it("returns true when demo query param is set", () => {
    expect(readPresenterMode("?demo=1")).toBe(true);
  });

  it("returns false when flags are absent", () => {
    expect(readPresenterMode("")).toBe(false);
    expect(readPresenterMode("?presenter=0")).toBe(false);
  });
});
