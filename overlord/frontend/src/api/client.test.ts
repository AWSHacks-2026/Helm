import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchHistory } from "./client";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("encodes session ids when fetching history", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchHistory("team/a b?c");

    expect(fetchMock).toHaveBeenCalledWith("/api/history?session_id=team%2Fa+b%3Fc");
  });
});
