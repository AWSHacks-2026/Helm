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
  title: "Agent fleets are starting to thrash like uncoordinated threads.",
  lede:
    "Agentic AI lets teams launch many coding agents at once, but those agents often share the same repo, files, tests, and product goals. Without coordination, they duplicate work, overwrite each other, and spend tokens repairing damage they created.",
  metrics: [
    {
      value: "Duplicate tasks",
      label: "Two agents solve the same job",
      body:
        "When agents receive overlapping prompts or discover the same failing area, they can both edit the same file and burn separate context windows on one piece of work.",
    },
    {
      value: "Token burn",
      label: "The cost compounds",
      body:
        "Thrashing turns one useful model call into rounds of rebuild, rebase, re-test, and repair. The customer pays in tokens, latency, CI minutes, and review time.",
    },
    {
      value: "Human drag",
      label: "Engineers become traffic cops",
      body:
        "Instead of reviewing finished work, people using agentic AI have to inspect conflicts, decide which agent is right, and clean up duplicated changes.",
    },
  ],
  sections: [
    {
      title: "What thrashing means",
      body:
        "Thrashing is when agents make progress locally but waste work globally. One agent fixes auth while another rewrites the same auth file, a third reverts part of it, and the team spends the next loop resolving the collision.",
    },
    {
      title: "Why agents do it",
      body:
        "Most coding agents optimize for their own prompt. They do not automatically know which files peers are editing, which intent already exists, or whether another agent has claimed the same task.",
    },
    {
      title: "Why it becomes common",
      body:
        "The moment teams run more than one agent against the same repo, shared resources appear: files, tests, APIs, product requirements, and git history. More parallelism creates more chances for overlap.",
    },
    {
      title: "Who feels the pain",
      body:
        "Developers, reviewers, and platform teams feel it first. They see higher model bills, slower demos, noisy pull requests, merge conflicts, and less trust in autonomous agents.",
    },
  ],
};

export const SOLUTION_PAGE: PresentationPageContent = {
  eyebrow: "Our Solution",
  title: "Overlord is the coordinator above the agent fleet.",
  lede:
    "The simple idea: let agents work in parallel, but give them a shared operator that can see intent, detect collisions, block unsafe writes, and resolve conflicts once.",
  metrics: [
    {
      value: "1",
      label: "Agents declare intent",
      body:
        "Before work gets expensive, Helm records what each agent plans to touch and checks whether another agent is already nearby.",
    },
    {
      value: "2",
      label: "Helm manages shared resources",
      body:
        "Like a concurrency controller for threads, Helm decides when agents can proceed, when they need arbitration, and when duplicate work should be reassigned.",
    },
    {
      value: "3",
      label: "Customers get work back",
      body:
        "The result is fewer wasted model calls, fewer collisions, safer writes, and a Gratitude ledger that shows the time and tokens returned.",
    },
  ],
  sections: [
    {
      title: "The five-year-old version",
      body:
        "Imagine several people coloring one picture at the same time. If nobody talks, two people may color the same part or erase each other. Overlord is the grown-up at the table who says, you take the sky, you take the trees, and stop before you spill paint.",
    },
    {
      title: "The technical analogy",
      body:
        "This is the dining philosophers problem for agentic software work. Threads need coordination when they share resources. Agents need coordination when they share files, tests, memory, and product intent.",
    },
    {
      title: "What Helm does",
      body:
        "Helm gates contention, deduplicates overlapping tasks, applies guardrails before risky writes, arbitrates hard merges with Bedrock, and records the savings in session history.",
    },
    {
      title: "Why it stays simple",
      body:
        "Overlord does not replace the agents. It gives them a lightweight control tower so each agent can stay focused while the system prevents fleet-level chaos.",
    },
  ],
};

export const TECHNICAL_WORKFLOW_PAGE: TechnicalWorkflowPageContent = {
  eyebrow: "Technical Workflow",
  title: "How Helm coordinates agent fleets on AWS.",
  lede:
    "Architecture first: coding agents declare work, Helm decides whether coordination is needed, Amazon Bedrock handles the hard arbitration, and session history feeds the Control Tower and Gratitude ledger.",
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
        "The presenter site is a TypeScript React app that renders replay state, incidents, gratitude, results, and this technical workflow.",
    },
    {
      value: "FastAPI :8000",
      label: "Helm coordination API",
      body:
        "Python 3.11, FastAPI, Uvicorn, in-memory stores, websocket broadcasts, and API routes for intents, guardrails, resolve, history, missions, and gratitude.",
    },
    {
      value: "ShopFix :8001",
      label: "Real benchmark target",
      body:
        "The Etsy-lite fixture gives Helm real git contention, auth/cart/listing files, and reproducible benchmark scenarios.",
    },
  ],
  sections: [
    {
      title: "AWS service usage",
      body:
        "Amazon Bedrock Runtime runs Anthropic Messages calls. AgentCore Memory stores session events with a local .helm/session.json fallback. AgentCore Policy represents Cedar-style preflight checks. AgentCore Runtime can host the merge arbitrator when HELM_ARBITRATOR_ARN is configured.",
    },
    {
      title: "Bedrock routing",
      body:
        "Claude Haiku 4.5 handles light coordination, agent work, guardrail checks, and cheaper merge paths. Claude Sonnet 4.6 handles fleet dedup, hard merges, and multi-agent arbitration when complexity crosses the routing threshold.",
    },
    {
      title: "Two decisions, not one",
      body:
        "Contention gate asks: should we spend Bedrock on coordination? Guardrails ask: may this agent write this file? They compose; neither replaces the other.",
    },
    {
      title: "Judge demo mode",
      body:
        "HELM_MOCK_BEDROCK=1 swaps live Bedrock calls for local simulators, while replay events still sync through POST /history/event so the Gratitude ledger shows returned time and tokens.",
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
