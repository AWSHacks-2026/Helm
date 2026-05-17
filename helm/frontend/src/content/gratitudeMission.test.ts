import { describe, expect, it } from "vitest";

import {
  GRATITUDE_INTRO,
  GRATITUDE_WHY,
  HACKATHON_HOOK,
  HACKATHON_THEME,
  HELM_MARK_ARIA,
  HELM_TAGLINE,
  MISSIONS_INTRO,
  PRODUCT_NAME,
  ROADMAP_ITEMS,
} from "./gratitudeMission";

describe("gratitudeMission", () => {
  it("defines hackathon theme and copy", () => {
    expect(HACKATHON_THEME).toBe("Build with Gratitude");
    expect(PRODUCT_NAME).toBe("Helm");
    expect(GRATITUDE_WHY).toMatch(/parents/i);
    expect(HACKATHON_HOOK).toMatch(/merge conflicts/i);
    expect(GRATITUDE_INTRO).toMatch(/time you get back/i);
    expect(ROADMAP_ITEMS.length).toBeGreaterThanOrEqual(3);
    expect(ROADMAP_ITEMS.map((item) => item.id)).toEqual(
      expect.arrayContaining(["intent", "fleet", "cicd"]),
    );
    expect(MISSIONS_INTRO.title).toMatch(/Mission/i);
  });
});

describe("gratitudeMission brand bridge", () => {
  it("connects Helm navigation to Gratitude payoff", () => {
    expect(HELM_TAGLINE).toMatch(/steer/i);
    expect(HELM_TAGLINE).toMatch(/gave back/i);
    expect(HELM_MARK_ARIA).toContain("Helm");
    expect(HACKATHON_THEME).toBe("Build with Gratitude");
    expect(PRODUCT_NAME).toBe("Helm");
  });
});
