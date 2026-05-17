import type { AgentState, IncidentState, TimelineEvent } from "./types";

const T0 = "2026-05-17T16:00:00.000Z";

const agent = (
  id: string,
  name: string,
  taskTitle: string,
  filePath: string,
): AgentState => ({
  id,
  name,
  status: "coding",
  taskTitle,
  filePath,
});

const incident = (
  id: string,
  type: IncidentState["type"],
  status: IncidentState["status"],
  title: string,
  summary: string,
  agentIds: string[],
  timestamp: string,
  suggestedTask?: string,
): IncidentState => ({
  id,
  type,
  status,
  title,
  summary,
  agentIds,
  suggestedTask,
  createdAt: timestamp,
});

/** ShopFix contention-style replay for judge demos (auth.py overlap + guardrail). */
export const createShopfixDemoReplayEvents = (): TimelineEvent[] => {
  const authPath = "backend/app/routers/auth.py";
  const cartPath = "backend/app/routers/cart.py";
  const catalogPath = "backend/app/routers/catalog.py";
  const ordersPath = "backend/app/routers/orders.py";
  const paymentsPath = "backend/app/routers/payments.py";
  const listingsPath = "backend/app/routers/listings.py";

  const duplicateIncident = incident(
    "incident-auth-dedup",
    "duplicate_work",
    "open",
    "Duplicate work on ShopFix auth.py",
    "agent_a and agent_b both target session TTL and OAuth on the same router file.",
    ["agent_a", "agent_b"],
    "2026-05-17T16:03:00.000Z",
    "Extend cart checkout validation",
  );

  const guardrailIncident = incident(
    "incident-auth-guardrail",
    "guardrail_block",
    "blocked",
    "Guardrail blocked destructive auth change",
    "reverses_recent_decision: delete session store blocked before write.",
    ["agent_b"],
    "2026-05-17T16:05:00.000Z",
  );

  return [
    {
      id: "sf-001",
      timestamp: T0,
      kind: "agent_started",
      title: "agent_a started on auth.py",
      description: "Session TTL hardening on ShopFix auth router.",
      agent: agent("agent_a", "agent_a", "Harden session TTL", authPath),
    },
    {
      id: "sf-002",
      timestamp: "2026-05-17T16:00:12.000Z",
      kind: "agent_started",
      title: "agent_b started on auth.py",
      description: "OAuth callback validation on the same file.",
      agent: agent("agent_b", "agent_b", "OAuth callback validation", authPath),
    },
    {
      id: "sf-003",
      timestamp: "2026-05-17T16:00:24.000Z",
      kind: "agent_started",
      title: "agent_c started on cart.py",
      description: "Disjoint file. No contention.",
      agent: agent("agent_c", "agent_c", "Cart merge rules", cartPath),
    },
    {
      id: "sf-004",
      timestamp: "2026-05-17T16:00:36.000Z",
      kind: "agent_started",
      title: "agent_d started on catalog.py",
      description: "Disjoint catalog facets work.",
      agent: agent("agent_d", "agent_d", "Catalog facets", catalogPath),
    },
    {
      id: "sf-005",
      timestamp: "2026-05-17T16:00:48.000Z",
      kind: "agent_started",
      title: "agent_e started on orders.py",
      description: "Disjoint orders export path.",
      agent: agent("agent_e", "agent_e", "Order export hooks", ordersPath),
    },
    {
      id: "sf-006",
      timestamp: "2026-05-17T16:01:00.000Z",
      kind: "agent_started",
      title: "agent_f started on payments.py",
      description: "Disjoint payments reconciliation.",
      agent: agent("agent_f", "agent_f", "Payment reconciliation", paymentsPath),
    },
    {
      id: "sf-007",
      timestamp: "2026-05-17T16:02:00.000Z",
      kind: "intent_declared",
      title: "agent_a registered task on auth.py",
      description: "Session TTL work tracked on the auth router.",
      agentId: "agent_a",
      taskTitle: "Harden session TTL",
      filePath: authPath,
    },
    {
      id: "sf-008",
      timestamp: "2026-05-17T16:02:30.000Z",
      kind: "intent_declared",
      title: "agent_b registered task on auth.py",
      description: "OAuth validation overlaps agent_a on the same file.",
      agentId: "agent_b",
      taskTitle: "OAuth callback validation",
      filePath: authPath,
    },
    {
      id: "sf-009",
      timestamp: "2026-05-17T16:03:00.000Z",
      kind: "duplicate_detected",
      title: "Fleet dedup on auth.py",
      description: "Helm detected duplicate work. Gate arbitrate, fleet dedup call.",
      agentIds: ["agent_a", "agent_b"],
      blockedAgentIds: ["agent_b"],
      incident: duplicateIncident,
    },
    {
      id: "sf-010",
      timestamp: "2026-05-17T16:04:00.000Z",
      kind: "agent_reassigned",
      title: "agent_b reassigned to listings.py",
      description: "Loser redirected to disjoint fill file after dedup trim.",
      agentId: "agent_b",
      taskTitle: "Listing search facets",
      filePath: listingsPath,
    },
    {
      id: "sf-011",
      timestamp: "2026-05-17T16:05:00.000Z",
      kind: "guardrail_blocked",
      title: "Guardrail blocked destructive auth edit",
      description: "ShopFix auth.py: block before write on session delete.",
      agentId: "agent_b",
      incident: guardrailIncident,
    },
    {
      id: "sf-012",
      timestamp: "2026-05-17T16:06:00.000Z",
      kind: "benchmark_result",
      title: "ShopFix live benchmark",
      description: "Contention N=8: +18% cost, +39% wall vs baseline (6 agents run).",
      benchmark: {
        tokenSavingsLabel: "18%",
        baselineTokens: 2400,
        overlordTokens: 1320,
      },
    },
    {
      id: "sf-013",
      timestamp: "2026-05-17T16:06:30.000Z",
      kind: "intent_declared",
      title: "Fleet coordinated on ShopFix",
      description:
        "Dedup resolved, destructive auth edit blocked, benchmark logged. Fleet steady.",
      agentId: "agent_a",
      taskTitle: "Harden session TTL",
      filePath: authPath,
    },
  ];
};
