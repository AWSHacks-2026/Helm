export type PresentationMetric = {
  value: string;
  label: string;
  body: string;
};

export type PresentationSection = {
  title: string;
  body: string;
};

export type PresentationPageContent = {
  eyebrow: string;
  title: string;
  lede: string;
  metrics: PresentationMetric[];
  sections: PresentationSection[];
};

export type TechnicalNode = {
  title: string;
  detail: string;
  tone: "teal" | "purple" | "coral" | "amber" | "blue" | "gray" | "green" | "red";
};

export type TechnicalLane = {
  label: string;
  nodes: TechnicalNode[];
  note?: string;
};

export type TechnicalWorkflowPageContent = PresentationPageContent & {
  badges: string[];
  lanes: TechnicalLane[];
  envSwitches: Array<{ name: string; value: string }>;
};

export const PROBLEM_PAGE: PresentationPageContent = {
  eyebrow: "Problem Statement",
  title: "Agent fleets thrash when nobody owns the shared repo.",
  lede:
    "You can spin up many coding agents at once, but they still share files, tests, and product goals. Without a coordinator, they duplicate work, overwrite each other, and spend tokens fixing collisions they created.",
  metrics: [
    {
      value: "Duplicate tasks",
      label: "Two agents, one file",
      body:
        "Overlapping prompts or the same failing test send two agents to auth.py. Both burn context on work that only needed one owner.",
    },
    {
      value: "Token burn",
      label: "Cost stacks fast",
      body:
        "One useful model call turns into rebuild, rebase, re-test, and repair. You pay in tokens, latency, CI minutes, and review time.",
    },
    {
      value: "Human drag",
      label: "Engineers as traffic cops",
      body:
        "Instead of reviewing finished work, people inspect conflicts, pick a winner, and clean up duplicate diffs.",
    },
  ],
  sections: [
    {
      title: "What thrashing means",
      body:
        "Agents make local progress but waste global effort. One fixes auth while another rewrites the same module, a third partially reverts it, and the team spends the next hour untangling the mess.",
    },
    {
      title: "Why agents do it",
      body:
        "Most agents optimize for their own prompt. They do not automatically see peer intents, file claims, or tasks another agent already took.",
    },
    {
      title: "Why it gets worse",
      body:
        "More agents on one repo means more shared surfaces: files, APIs, tests, git history. Parallelism without coordination is overlap waiting to happen.",
    },
    {
      title: "Who feels it",
      body:
        "Developers and platform teams see higher bills, slower demos, noisy PRs, and less trust that autonomous agents are safe to run wide open.",
    },
  ],
};

export const SOLUTION_PAGE: PresentationPageContent = {
  eyebrow: "Our Solution",
  title: "Helm is the coordination layer above your agent fleet.",
  lede:
    "Let agents work in parallel, but give them one operator that sees intent, spots collisions, blocks unsafe writes, and resolves hard merges once.",
  metrics: [
    {
      value: "1",
      label: "Agents declare intent",
      body:
        "Before work gets expensive, Helm records what each agent plans to touch and whether another agent is already there.",
    },
    {
      value: "2",
      label: "Helm manages shared resources",
      body:
        "Like a lock for threads, Helm decides when agents proceed, when to arbitrate, and when duplicate work should be reassigned.",
    },
    {
      value: "3",
      label: "You get work back",
      body:
        "Fewer wasted model calls, fewer collisions, safer writes, and a Gratitude ledger that shows time and tokens returned.",
    },
  ],
  sections: [
    {
      title: "The simple version",
      body:
        "Picture several people coloring one page. Without rules, two people color the same corner. Helm is the person at the table who assigns regions and stops someone from erasing fresh ink.",
    },
    {
      title: "The CS version",
      body:
        "This is dining philosophers for agentic coding. Shared files need coordination the same way shared memory does for threads.",
    },
    {
      title: "What Helm does",
      body:
        "Gates contention, deduplicates overlap, guardrails risky writes, arbitrates merges with Bedrock when needed, and logs savings to session history.",
    },
    {
      title: "What Helm is not",
      body:
        "Helm does not replace your agents. It is a lightweight control tower so each agent stays focused while the fleet avoids pile-ups.",
    },
  ],
};

export const TECHNICAL_WORKFLOW_PAGE: TechnicalWorkflowPageContent = {
  eyebrow: "Technical Workflow",
  title: "How Helm coordinates agent fleets on AWS.",
  lede:
    "Agents declare work. Helm decides if coordination is worth a Bedrock call. Amazon Bedrock handles hard arbitration. Session history feeds the Control Tower and Gratitude ledger.",
  badges: [
    "Bedrock Claude Haiku 4.5",
    "Bedrock Claude Sonnet 4.6",
    "AgentCore Memory / Policy / Runtime",
  ],
  metrics: [
    {
      value: "React 19 + Vite",
      label: "Control Tower UI",
      body:
        "TypeScript React app for replay, incidents, gratitude, results, flight recorder, and this workflow view.",
    },
    {
      value: "FastAPI :8000",
      label: "Helm coordination API",
      body:
        "Python 3.11, FastAPI, in-memory stores, websockets, and routes for intents, guardrails, resolve, history, missions, and gratitude.",
    },
    {
      value: "ShopFix :8001",
      label: "Real benchmark target",
      body:
        "Etsy-lite fixture with real git sandboxes for auth, cart, and listing contention.",
    },
  ],
  sections: [
    {
      title: "AWS service usage",
      body:
        "Bedrock Runtime runs Anthropic Messages. AgentCore Memory stores session events with a local .helm/session.json fallback. AgentCore Policy mirrors Cedar-style preflight. AgentCore Runtime can host the merge arbitrator when HELM_ARBITRATOR_ARN is set.",
    },
    {
      title: "Bedrock routing",
      body:
        "Haiku 4.5 for light coordination and agent edits. Sonnet 4.6 for fleet dedup and hard merges when complexity crosses the threshold.",
    },
    {
      title: "Two decisions, not one",
      body:
        "Contention gate asks: should we spend Bedrock on coordination? Guardrails ask: may this agent write this file? They stack. Neither replaces the other.",
    },
    {
      title: "Judge demo mode",
      body:
        "HELM_MOCK_BEDROCK=1 uses local simulators. Replay still syncs through POST /history/event so Gratitude shows returned time and tokens.",
    },
  ],
  lanes: [
    {
      label: "Agents",
      nodes: [
        { title: "Coding agents", detail: "Cursor / Claude Code / MCP", tone: "teal" },
        { title: "ShopFix harness", detail: "git benchmark :8001", tone: "teal" },
        { title: "Control Tower", detail: "React/Vite :5173", tone: "blue" },
      ],
    },
    {
      label: "Helm API",
      nodes: [
        { title: "POST /intents", detail: "declare work", tone: "gray" },
        { title: "POST /guardrails", detail: "/check + demo check", tone: "gray" },
        { title: "POST /resolve", detail: "merge conflict", tone: "gray" },
        { title: "POST /missions/delegate", detail: "fleet dedup", tone: "gray" },
        { title: "GET /gratitude", detail: "ledger endpoint", tone: "green" },
        { title: "WS /ws/conflicts", detail: "live broadcast", tone: "gray" },
      ],
    },
    {
      label: "Coordination",
      nodes: [
        { title: "Contention gate", detail: "allow skips Bedrock", tone: "amber" },
        { title: "Guardrails", detail: "write safety always runs", tone: "teal" },
        { title: "Inference routing", detail: "Haiku or Sonnet", tone: "purple" },
        { title: "Fleet dedup", detail: "continue one, reassign rest", tone: "green" },
      ],
      note: "HELM_GATE_ENABLED, assess_intent, assess_dedup, preflight_check",
    },
    {
      label: "AWS Bedrock",
      nodes: [
        { title: "Claude Haiku 4.5", detail: "agents / guardrails / light merge", tone: "teal" },
        { title: "Claude Sonnet 4.6", detail: "fleet dedup / hard merges", tone: "coral" },
        { title: "AgentCore Memory", detail: "session log / local fallback", tone: "purple" },
        { title: "AgentCore Policy", detail: "Cedar preflight on writes", tone: "purple" },
        { title: "AgentCore Runtime", detail: "optional merge arbitrator", tone: "amber" },
      ],
    },
    {
      label: "Judge UI",
      nodes: [
        { title: "useDemoReplay", detail: "scripted timeline", tone: "gray" },
        { title: "syncReplayToLedger", detail: "POST /history/event", tone: "gray" },
        { title: "ControlTower", detail: "timeline + incidents", tone: "blue" },
        { title: "BenchmarkProof", detail: "static charts + pillars", tone: "green" },
      ],
    },
    {
      label: "Stores",
      nodes: [
        { title: "SessionStore", detail: "intents per file / RAM", tone: "gray" },
        { title: "ConflictStore", detail: "active conflicts / RAM", tone: "gray" },
        { title: "MissionStore", detail: "fleet assignments / RAM", tone: "gray" },
        { title: "GratitudeLedger", detail: "blocked / deduped / tokens", tone: "green" },
      ],
    },
  ],
  envSwitches: [
    { name: "HELM_MOCK_BEDROCK", value: "1 demo / 0 live" },
    { name: "HELM_USE_LOCAL_MEMORY", value: "true / false" },
    { name: "HELM_USE_LOCAL_POLICY", value: "true / false" },
    { name: "HELM_GATE_ENABLED", value: "1" },
  ],
};
