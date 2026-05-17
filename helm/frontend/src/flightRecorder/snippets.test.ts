import { describe, expect, it } from "vitest";

import { SNIPPET_KEYS, getSnippet } from "./snippets";

describe("snippets", () => {
  it("exposes auth and cart excerpt keys", () => {
    expect(SNIPPET_KEYS).toContain("auth_clean");
    expect(SNIPPET_KEYS).toContain("cart_conflict");
    expect(getSnippet("auth_clean")).toContain("login");
  });
});
