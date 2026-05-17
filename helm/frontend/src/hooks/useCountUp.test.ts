/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useCountUp } from "./useCountUp";

describe("useCountUp", () => {
  beforeEach(() => {
    vi.stubGlobal("requestAnimationFrame", (fn: FrameRequestCallback) => {
      fn(performance.now() + 600);
      return 1;
    });
    vi.stubGlobal("cancelAnimationFrame", () => undefined);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("animates from 0 to target when motion allowed", () => {
    const { result } = renderHook(() =>
      useCountUp(100, { durationMs: 600, enabled: true }),
    );
    expect(result.current).toBe(100);
  });

  it("jumps to target when disabled", () => {
    const { result } = renderHook(() =>
      useCountUp(42, { durationMs: 600, enabled: false }),
    );
    expect(result.current).toBe(42);
  });
});
