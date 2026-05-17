/** AWS Hackathon 2026 — track theme; load-bearing for product copy. */
export const HACKATHON_THEME = "Build with Gratitude";

/** Hackathon product name (judge-facing). */
export const PRODUCT_NAME = "Overlord";

/** Engineering name for the coordination API and Control Tower. */
export const TECH_NAME = "Helm";

/** Nav / logo — Helm coordinates; Gratitude is the receipt. */
export const HELM_TAGLINE = "Steer the fleet. See what you gave back.";

export const HELM_MARK_ARIA =
  "Helm — coordination control tower for Build with Gratitude";

/**
 * Why we built this — not interchangeable with “kindness” or “wellness.”
 * Parents’ careers → merge conflicts, agent collisions, wasted compute → time back.
 */
export const GRATITUDE_WHY =
  "Our parents spent careers in software engineering watching hours disappear to merge conflicts, agents stepping on each other's work, and compute burned on rework. We built Overlord for them — and for every engineer still grinding through the same chaos.";

/** Landing hero — one emotional beat, then proof. */
export const HACKATHON_HOOK = GRATITUDE_WHY;

/** Gratitude page lede — theme is the ledger itself. */
export const GRATITUDE_INTRO =
  "Every number here is time returned: a blocked bad write, a duplicate mission cut, a merge settled once instead of thrashed. This session is our thank-you — coordination that pays back the people who taught us the craft.";

export const GRATITUDE_SESSION_TITLE = "What we gave back this session";

export const GRATITUDE_EMPTY_HINT =
  "Run the guided demo, wait for replay to finish, then refresh — each coordination win lands here as time and tokens you did not waste.";

export const GRATITUDE_LOADING = "Tallying what Overlord returned to this session…";

export const GRATITUDE_ERROR_NO_SESSION =
  "Set a session ID on the landing page (try mergeai-hackathon-demo) so we can show what was returned.";

export const GRATITUDE_ERROR_FETCH =
  "Could not reach the gratitude ledger — is Helm running on :8000? Every blocked write and deduped mission should still be waiting in session memory.";

export const ROADMAP_EYEBROW = "Paying it forward";

export const ROADMAP_ITEMS = [
  {
    id: "intent",
    title: "Intent coordination",
    body: "Agents declare what they plan to edit before touching a file — so parents’ generation of “find out at merge time” becomes “align before the damage.” API is live; full judge UI flow is next.",
  },
  {
    id: "fleet",
    title: "Fleet sessions across machines",
    body: "Multiple laptops share one Helm coordinator (HELM_API_BASE) so every agent writes into one ledger — gratitude scales when the whole team stops colliding.",
  },
  {
    id: "cicd",
    title: "CI/CD guardrails",
    body: "GitHub Actions calls the same guardrails and merge arbitration as local agents — time saved on every PR, not just every demo.",
  },
] as const;

export const MISSIONS_INTRO = {
  eyebrow: "GitHub delegation",
  title: "Mission queue",
  body: "Load issues, delegate to agents, and let Overlord trim overlap before anyone burns a context window on duplicate auth.py work.",
} as const;

/** Presenter / README one-liner. */
export const GRATITUDE_PITCH =
  "Overlord coordinates agent fleets on Amazon Bedrock — gate contention, dedupe overlap, block bad writes, merge once. The Gratitude ledger is the proof: time and tokens given back.";

/** Results tab — tie benchmarks to the mission. */
export const RESULTS_INTRO =
  "Measured on ShopFix with real git — savings we would hand to the engineers who raised us: fewer Sonnet calls when work is disjoint, fewer rebuilds when guardrails fire early.";
