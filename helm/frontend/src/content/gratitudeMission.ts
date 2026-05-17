/** AWS Hackathon 2026. Theme copy is load-bearing for the product. */
export const HACKATHON_THEME = "Build with Gratitude";

/** Product name shown in the UI. */
export const PRODUCT_NAME = "Helm";

/** Same as PRODUCT_NAME; kept for imports that distinguish API vs UI. */
export const TECH_NAME = "Helm";

export const HELM_TAGLINE = "Steer the agent fleet. See what you gave back.";

export const HELM_MARK_ARIA =
  "Helm control tower for Build with Gratitude";

export const GRATITUDE_WHY =
  "Our parents spent decades in software watching evenings vanish to merge conflicts, agents colliding on the same files, and models burning tokens on rework. We built Helm for them, and for anyone still running a crowded agent fleet on one repo.";

export const HACKATHON_HOOK = GRATITUDE_WHY;

export const GRATITUDE_INTRO =
  "Every number here is time you get back: a risky write stopped, duplicate work cut, a merge handled once instead of thrashed. This session is our thank-you to the people who taught us the craft.";

export const GRATITUDE_SESSION_TITLE = "What we gave back this session";

export const GRATITUDE_EMPTY_HINT =
  "Run the guided demo, wait for replay to finish, then hit refresh. Each win shows up here as time and tokens you did not waste.";

export const GRATITUDE_LOADING = "Counting what Helm returned to this session…";

export const GRATITUDE_ERROR_NO_SESSION =
  "Add a session ID on the landing page (try mergeai-hackathon-demo) so we can show what came back.";

export const GRATITUDE_ERROR_FETCH =
  "Could not reach the gratitude ledger. Is Helm running on port 8000? Blocked writes and deduped missions should still be in session memory.";

export const ROADMAP_EYEBROW = "Paying it forward";

export const ROADMAP_ITEMS = [
  {
    id: "intent",
    title: "Intent coordination",
    body: "Agents say what they plan to edit before they touch a file. Less surprise at merge time, more align-up-front. The API is live; the full judge flow in the UI is next.",
  },
  {
    id: "fleet",
    title: "Fleet sessions across machines",
    body: "Point every laptop at the same Helm host (HELM_API_BASE) so all agents share one ledger. Gratitude scales when the whole fleet stops stepping on itself.",
  },
  {
    id: "cicd",
    title: "CI/CD guardrails",
    body: "GitHub Actions can call the same guardrails and merge arbitration as your local agents. Savings on every PR, not just the demo.",
  },
] as const;

export const MISSIONS_INTRO = {
  eyebrow: "GitHub delegation",
  title: "Mission queue",
  body: "Load issues, delegate to agents, and let Helm trim overlap before anyone burns a context window on the same auth.py patch.",
} as const;

export const GRATITUDE_PITCH =
  "Helm coordinates coding agent fleets on Amazon Bedrock: gate contention, dedupe overlap, block bad writes, merge once. The Gratitude ledger is the receipt for time and tokens you kept.";

export const RESULTS_INTRO =
  "Measured on ShopFix with real git. Fewer Sonnet calls when work is disjoint, fewer rebuilds when guardrails fire early. That is compute you do not ship to rework.";
