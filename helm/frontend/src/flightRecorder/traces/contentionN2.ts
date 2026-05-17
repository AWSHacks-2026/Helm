import { demoAgent, demoIncident } from "../../orchestration/demoScenarioHelpers";
import type { TimelineEvent } from "../../orchestration/types";
import { buildTraceFrames, type TraceSnippetMap } from "../buildTraceFrames";
import type { FlightTrace } from "../types";

const AUTH_PATH = "backend/app/routers/auth.py";
const LISTINGS_PATH = "backend/app/routers/listings.py";
const T0 = "2026-05-17T16:00:00.000Z";

export const CONTENTION_N2_SNIPPETS: TraceSnippetMap = {
  clean: "auth_clean",
  edit_a: "auth_agent_a_edit",
  edit_b: "auth_agent_b_edit",
  conflict: "auth_agent_b_edit",
  merged: "auth_agent_a_edit",
  blocked: "auth_guardrail_blocked",
};

const createContentionN2Events = (): TimelineEvent[] => {
  const duplicateIncident = demoIncident(
    "incident-auth-dedup-n2",
    "duplicate_work",
    "open",
    "Duplicate work on ShopFix auth.py",
    "agent_a and agent_b both target session TTL and OAuth on the same router file.",
    ["agent_a", "agent_b"],
    "2026-05-17T16:03:00.000Z",
    { filePath: AUTH_PATH, suggestedTask: "Extend cart checkout validation" },
  );

  const guardrailIncident = demoIncident(
    "incident-auth-guardrail-n2",
    "guardrail_block",
    "blocked",
    "Guardrail blocked destructive auth change",
    "reverses_recent_decision: delete session store blocked before write.",
    ["agent_b"],
    "2026-05-17T16:05:00.000Z",
    { filePath: AUTH_PATH },
  );

  return [
    {
      id: "n2-001",
      timestamp: T0,
      kind: "agent_started",
      title: "agent_a started on auth.py",
      description: "Session TTL hardening on ShopFix auth router.",
      agent: demoAgent("agent_a", "agent_a", "Harden session TTL", AUTH_PATH),
    },
    {
      id: "n2-002",
      timestamp: "2026-05-17T16:00:12.000Z",
      kind: "agent_started",
      title: "agent_b started on auth.py",
      description: "OAuth callback validation on the same file.",
      agent: demoAgent("agent_b", "agent_b", "OAuth callback validation", AUTH_PATH),
    },
    {
      id: "n2-003",
      timestamp: "2026-05-17T16:02:00.000Z",
      kind: "intent_declared",
      title: "agent_a registered task on auth.py",
      description: "Session TTL work tracked on the auth router.",
      agentId: "agent_a",
      taskTitle: "Harden session TTL",
      filePath: AUTH_PATH,
    },
    {
      id: "n2-004",
      timestamp: "2026-05-17T16:02:30.000Z",
      kind: "intent_declared",
      title: "agent_b registered task on auth.py",
      description: "OAuth validation overlaps agent_a on the same file.",
      agentId: "agent_b",
      taskTitle: "OAuth callback validation",
      filePath: AUTH_PATH,
    },
    {
      id: "n2-005",
      timestamp: "2026-05-17T16:03:00.000Z",
      kind: "duplicate_detected",
      title: "Fleet dedup on auth.py",
      description: "Helm detected duplicate work. Gate arbitrate, fleet dedup call.",
      agentIds: ["agent_a", "agent_b"],
      blockedAgentIds: ["agent_b"],
      incident: duplicateIncident,
    },
    {
      id: "n2-006",
      timestamp: "2026-05-17T16:04:00.000Z",
      kind: "agent_reassigned",
      title: "agent_b reassigned to listings.py",
      description: "Loser redirected to disjoint file after dedup trim.",
      agentId: "agent_b",
      taskTitle: "Listing search facets",
      filePath: LISTINGS_PATH,
    },
    {
      id: "n2-007",
      timestamp: "2026-05-17T16:05:00.000Z",
      kind: "guardrail_blocked",
      title: "Guardrail blocked destructive auth edit",
      description: "ShopFix auth.py: block before write on session delete.",
      agentId: "agent_b",
      incident: guardrailIncident,
    },
  ];
};

export function loadContentionN2Trace(): FlightTrace {
  const events = createContentionN2Events();
  return {
    id: "contention_n2",
    label: "N=2 · Fleet dedup (auth.py)",
    description:
      "Two agents overlap on auth.py. Helm dedupes, reassigns agent_b, and blocks a destructive write.",
    frames: buildTraceFrames(events, {
      primaryFile: AUTH_PATH,
      agentIds: ["agent_a", "agent_b"],
      snippets: CONTENTION_N2_SNIPPETS,
    }),
  };
}
