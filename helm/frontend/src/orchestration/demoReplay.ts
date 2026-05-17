import type { AgentState, AgentTask, IncidentState, TimelineEvent } from "./types";

const startedAt = "2026-05-16T16:00:00.000Z";

const agentTask = (id: string, title: string, domain: string): AgentTask => ({
  id,
  title,
  domain,
});

const agentState = (
  id: string,
  name: string,
  task: AgentTask,
  timestamp: string,
): AgentState => ({
  id,
  name,
  status: "coding",
  taskTitle: task.title,
  filePath: `src/${task.domain}/${task.id}.ts`,
});

const incidentState = (
  id: string,
  type: IncidentState["type"],
  status: IncidentState["status"],
  title: string,
  summary: string,
  agentIds: string[],
  suggestedTask: string,
  timestamp: string,
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

export const createDemoReplayEvents = (): TimelineEvent[] => {
  const authSessionTask = agentTask(
    "task-auth-session",
    "Auth session hardening",
    "auth",
  );
  const authOauthTask = agentTask(
    "task-auth-oauth",
    "OAuth callback validation",
    "auth",
  );
  const catalogTask = agentTask(
    "task-catalog-facets",
    "Catalog facets and merchandising cards",
    "catalog",
  );
  const billingTask = agentTask(
    "task-billing-invoices",
    "Billing invoice export flow",
    "billing",
  );
  const cacheTask = agentTask(
    "task-cache-warmup",
    "Cache warming policy",
    "cache",
  );
  const searchTask = agentTask(
    "task-search-ranking",
    "Search filters and ranking controls",
    "search",
  );

  const duplicateIncident = incidentState(
    "incident-duplicate-auth",
    "duplicate_work",
    "open",
    "Duplicate auth work detected",
    "Agent 01 and Agent 02 are both changing overlapping auth session paths.",
    ["agent-01", "agent-02"],
    authSessionTask.title,
    "2026-05-16T16:03:00.000Z",
  );
  const guardrailIncident = incidentState(
    "incident-cache-guardrail",
    "guardrail_block",
    "blocked",
    "Cache policy guardrail blocked",
    "Agent 05 attempted to bypass the shared cache invalidation contract.",
    ["agent-05"],
    cacheTask.title,
    "2026-05-16T16:06:00.000Z",
  );
  const mergeIncident = incidentState(
    "incident-billing-merge",
    "merge_conflict",
    "open",
    "Billing export merge conflict",
    "Billing invoice export changes require human review before merge.",
    ["agent-04"],
    billingTask.title,
    "2026-05-16T16:07:00.000Z",
  );

  return [
    {
      id: "event-001",
      timestamp: "2026-05-16T16:00:00.000Z",
      kind: "agent_started",
      title: "Agent 01 started auth session work",
      description: "Agent 01 began hardening auth session behavior.",
      agent: agentState(
        "agent-01",
        "Agent 01",
        authSessionTask,
        "2026-05-16T16:00:00.000Z",
      ),
    },
    {
      id: "event-002",
      timestamp: "2026-05-16T16:00:15.000Z",
      kind: "agent_started",
      title: "Agent 02 started auth callback work",
      description: "Agent 02 began validating OAuth callback edge cases.",
      agent: agentState(
        "agent-02",
        "Agent 02",
        authOauthTask,
        "2026-05-16T16:00:15.000Z",
      ),
    },
    {
      id: "event-003",
      timestamp: "2026-05-16T16:00:30.000Z",
      kind: "agent_started",
      title: "Agent 03 started catalog work",
      description: "Agent 03 began catalog facets and merchandising cards.",
      agent: agentState(
        "agent-03",
        "Agent 03",
        catalogTask,
        "2026-05-16T16:00:30.000Z",
      ),
    },
    {
      id: "event-004",
      timestamp: "2026-05-16T16:00:45.000Z",
      kind: "agent_started",
      title: "Agent 04 started billing work",
      description: "Agent 04 began billing invoice export work.",
      agent: agentState(
        "agent-04",
        "Agent 04",
        billingTask,
        "2026-05-16T16:00:45.000Z",
      ),
    },
    {
      id: "event-005",
      timestamp: "2026-05-16T16:01:00.000Z",
      kind: "agent_started",
      title: "Agent 05 started cache work",
      description: "Agent 05 began cache warming policy changes.",
      agent: agentState(
        "agent-05",
        "Agent 05",
        cacheTask,
        "2026-05-16T16:01:00.000Z",
      ),
    },
    {
      id: "event-006",
      timestamp: "2026-05-16T16:01:15.000Z",
      kind: "agent_started",
      title: "Agent 06 started search work",
      description: "Agent 06 began search ranking controls.",
      agent: agentState(
        "agent-06",
        "Agent 06",
        searchTask,
        "2026-05-16T16:01:15.000Z",
      ),
    },
    {
      id: "event-007",
      timestamp: "2026-05-16T16:02:00.000Z",
      kind: "intent_declared",
      title: "Agent 04 declared billing export intent",
      description: "Billing export changes were registered with Helm.",
      agentId: "agent-04",
      taskTitle: billingTask.title,
    },
    {
      id: "event-008",
      timestamp: "2026-05-16T16:03:00.000Z",
      kind: "duplicate_detected",
      title: "Helm detected duplicate auth work",
      description: "Agent 01 and Agent 02 have overlapping auth intent.",
      agentIds: ["agent-01", "agent-02"],
      blockedAgentIds: ["agent-02"],
      incident: duplicateIncident,
    },
    {
      id: "event-009",
      timestamp: "2026-05-16T16:04:00.000Z",
      kind: "agent_reassigned",
      title: "Agent 02 reassigned to search controls",
      description: "Agent 02 moved from auth overlap to search filters.",
      agentId: "agent-02",
      taskTitle: searchTask.title,
      filePath: `src/${searchTask.domain}/${searchTask.id}.ts`,
    },
    {
      id: "event-010",
      timestamp: "2026-05-16T16:06:00.000Z",
      kind: "guardrail_blocked",
      title: "Helm blocked cache guardrail violation",
      description: "Agent 05 cache policy change needs contract review.",
      agentId: "agent-05",
      incident: guardrailIncident,
    },
    {
      id: "event-011",
      timestamp: "2026-05-16T16:07:00.000Z",
      kind: "merge_detected",
      title: "Billing merge conflict detected",
      description: "Billing export branch conflicts with invoice schema work.",
      agentId: "agent-04",
      incident: mergeIncident,
    },
    {
      id: "event-012",
      timestamp: "2026-05-16T16:08:00.000Z",
      kind: "merge_resolved",
      title: "Helm resolved catalog merge overlap",
      description: "Catalog card overlap was resolved without human review.",
      agentId: "agent-03",
    },
    {
      id: "event-013",
      timestamp: "2026-05-16T16:09:00.000Z",
      kind: "human_review",
      title: "Billing conflict queued for human review",
      description: "The open billing merge conflict remains in the incident console.",
      agentId: "agent-04",
    },
    {
      id: "event-014",
      timestamp: "2026-05-16T16:10:00.000Z",
      kind: "benchmark_result",
      title: "Token benchmark completed",
      description: "Helm replay reduced duplicate coordination tokens.",
      benchmark: {
        tokenSavingsLabel: "42%",
        baselineTokens: 42000,
        overlordTokens: 24360,
      },
    },
  ];
};
