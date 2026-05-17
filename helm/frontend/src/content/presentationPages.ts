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
