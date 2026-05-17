import { describe, expect, it } from "vitest";

import {
  GRATITUDE_INTRO,
  GRATITUDE_WHY,
  HACKATHON_HOOK,
  HACKATHON_THEME,
  MISSIONS_INTRO,
  PRODUCT_NAME,
  ROADMAP_ITEMS,
} from "./gratitudeMission";

describe("gratitudeMission", () => {
  it("defines hackathon theme and copy", () => {
    expect(HACKATHON_THEME).toBe("Build with Gratitude");
    expect(PRODUCT_NAME).toBe("Overlord");
    expect(GRATITUDE_WHY).toMatch(/parents/i);
    expect(HACKATHON_HOOK).toMatch(/merge conflicts/i);
    expect(GRATITUDE_INTRO).toMatch(/time returned/i);
    expect(ROADMAP_ITEMS.length).toBeGreaterThanOrEqual(3);
    expect(ROADMAP_ITEMS.map((item) => item.id)).toEqual(
      expect.arrayContaining(["intent", "fleet", "cicd"]),
    );
    expect(MISSIONS_INTRO.title).toMatch(/Mission/i);
  });
});
