import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const themeDir = dirname(fileURLToPath(import.meta.url));

describe("theme/tokens.css", () => {
  it("defines calm premium gratitude palette", () => {
    const css = readFileSync(join(themeDir, "tokens.css"), "utf8");
    const lower = css.toLowerCase();
    expect(lower).toContain("--bg-page: #fffcf8");
    expect(lower).toContain("--semantic-save:");
    expect(lower).toContain("--accent-primary:");
    expect(lower).toContain("--btn-bg:");
    expect(css).not.toContain("#070b12");
  });

  it("main styles reference design tokens not legacy dark canvas", () => {
    const styles = readFileSync(join(themeDir, "../styles.css"), "utf8");
    expect(styles).toContain("var(--bg-page)");
    expect(styles).not.toMatch(/background:\s*#070b12/);
  });

  it("pillar styles use semantic-save token", () => {
    const styles = readFileSync(join(themeDir, "../styles.css"), "utf8");
    expect(styles).toContain(".pillar-card");
    expect(styles).toMatch(/var\(--semantic-save\)/);
  });
});
