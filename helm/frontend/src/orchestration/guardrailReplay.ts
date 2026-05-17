import { formatAgentName } from "../content/agentPersonas";
import { demoAgent, demoIncident } from "./demoScenarioHelpers";
import type { TimelineEvent } from "./types";

const T0 = "2026-05-17T16:20:00.000Z";
const AUTH_PATH = "backend/app/routers/auth.py";
const LISTINGS_PATH = "backend/app/routers/listings.py";

/** ShopFix guardrail — destructive auth edit blocked before write. */
export const createGuardrailReplayEvents = (): TimelineEvent[] => {
  const guardrailIncident = demoIncident(
    "incident-auth-guardrail-solo",
    "guardrail_block",
    "blocked",
    "Guardrail blocked session store delete",
    `${formatAgentName("agent_b")} tried to remove the session table while ${formatAgentName("agent_a")} was hardening TTL (reverses_recent_decision).`,
    ["agent_b"],
    "2026-05-17T16:22:00.000Z",
    {
      filePath: AUTH_PATH,
      reasoning: "Policy reverses_recent_decision: destructive delete on shared auth router.",
      suggestedTask: "Listing search facets on disjoint file",
    },
  );

  return [
    {
      id: "gr-001",
      timestamp: T0,
      kind: "agent_started",
      title: `${formatAgentName("agent_a")} started on auth.py`,
      description: "Session TTL hardening in progress.",
      agent: demoAgent("agent_a", formatAgentName("agent_a"), "Harden session TTL", AUTH_PATH),
    },
    {
      id: "gr-002",
      timestamp: "2026-05-17T16:20:15.000Z",
      kind: "agent_started",
      title: `${formatAgentName("agent_b")} started on auth.py`,
      description: "OAuth validation on shared auth router.",
      agent: demoAgent("agent_b", formatAgentName("agent_b"), "OAuth callback validation", AUTH_PATH),
    },
    {
      id: "gr-003",
      timestamp: "2026-05-17T16:21:00.000Z",
      kind: "intent_declared",
      title: `${formatAgentName("agent_a")} registered task on auth.py`,
      description: "TTL policy tracked on auth router.",
      agentId: "agent_a",
      taskTitle: "Harden session TTL",
      filePath: AUTH_PATH,
    },
    {
      id: "gr-004",
      timestamp: "2026-05-17T16:21:30.000Z",
      kind: "intent_declared",
      title: `${formatAgentName("agent_b")} registered task on auth.py`,
      description: "Destructive edit path flagged by guardrail policy.",
      agentId: "agent_b",
      taskTitle: "OAuth callback validation",
      filePath: AUTH_PATH,
    },
    {
      id: "gr-005",
      timestamp: "2026-05-17T16:22:00.000Z",
      kind: "guardrail_blocked",
      title: "Guardrail blocked destructive auth edit",
      description: "ShopFix auth.py: block before write on session store delete.",
      agentId: "agent_b",
      incident: guardrailIncident,
    },
    {
      id: "gr-006",
      timestamp: "2026-05-17T16:22:30.000Z",
      kind: "agent_reassigned",
      title: `${formatAgentName("agent_b")} redirected to listings.py`,
      description: "Yielded to disjoint work after guardrail block.",
      agentId: "agent_b",
      taskTitle: "Listing search facets",
      filePath: LISTINGS_PATH,
    },
    {
      id: "gr-007",
      timestamp: "2026-05-17T16:23:00.000Z",
      kind: "benchmark_result",
      title: "Guardrail benchmark",
      description: "Blocked destructive delete. ~450 tokens of rework avoided.",
      benchmark: {
        tokenSavingsLabel: "12%",
        baselineTokens: 900,
        overlordTokens: 450,
      },
    },
  ];
};
