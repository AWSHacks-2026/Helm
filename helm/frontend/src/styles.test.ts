import { describe, expect, it } from "vitest";

import css from "./styles.css?raw";

describe("styles", () => {
  it("does not hide the last presenter nav item with legacy CSS", () => {
    expect(css).not.toContain("body.presenter-mode .app-nav button:last-child");
  });
});
