import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchConflictDetail, fetchConflicts, fetchHistory } from "./client";
import { fetchLiveSessionEvents } from "./orchestration";

vi.mock("./client", () => ({
  fetchConflictDetail: vi.fn(),
  fetchConflicts: vi.fn(),
  fetchHistory: vi.fn(),
}));

const mockedFetchConflictDetail = vi.mocked(fetchConflictDetail);
const mockedFetchConflicts = vi.mocked(fetchConflicts);
const mockedFetchHistory = vi.mocked(fetchHistory);

describe("fetchLiveSessionEvents", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockedFetchConflictDetail.mockRejectedValue(new Error("detail unavailable"));
  });

  it("normalizes conflicts and known history records into typed timeline events", async () => {
    mockedFetchConflicts.mockResolvedValue([
      {
        conflict_id: "conflict-1",
        session_id: "session-1",
        file_path: "src/auth/session.ts",
        status: "pending_approval",
        conflict_type: "duplicate_work",
        created_at: "2026-05-16T18:00:00.000Z",
        agent_a_id: "agent-01",
        agent_b_id: "agent-02",
      },
      {
        conflict_id: "conflict-2",
        session_id: "session-1",
        file_path: "src/billing/export.ts",
        status: "approved",
        conflict_type: "merge_conflict",
        created_at: "2026-05-16T18:01:00.000Z",
        agent_a_id: "agent-03",
        agent_b_id: "agent-04",
      },
      {
        conflict_id: "conflict-3",
        session_id: "session-1",
        file_path: "src/search/query.ts",
        status: "unexpected",
        conflict_type: "unknown",
        created_at: "2026-05-16T18:02:00.000Z",
        agent_a_id: "agent-05",
        agent_b_id: "agent-06",
      },
    ]);
    mockedFetchHistory.mockResolvedValue([
      {
        event_type: "intent_declared",
        created_at: "2026-05-16T17:59:00.000Z",
        payload: {
          agent_id: "agent-01",
          task_title: "Auth session hardening",
          file_path: "src/auth/session.ts",
        },
      },
      {
        event_type: "guardrail_blocked",
        timestamp: "2026-05-16T18:03:00.000Z",
        payload: {
          agent_id: "agent-07",
          summary: "Blocked unsafe cache invalidation",
        },
      },
      { event_type: "ignored", payload: { code: "large raw payload" } },
    ]);

    const events = await fetchLiveSessionEvents("session-1");

    expect(fetchConflicts).toHaveBeenCalledWith("session-1");
    expect(fetchHistory).toHaveBeenCalledWith("session-1");
    expect(events.map((event) => event.id)).toEqual(
      expect.arrayContaining([
        "conflict-conflict-1",
        "conflict-conflict-2",
        "conflict-conflict-3",
        "history-0",
        "history-1",
      ]),
    );
    expect(events.find((event) => event.id === "conflict-conflict-1")).toMatchObject({
      kind: "duplicate_detected",
      agentIds: ["agent-01", "agent-02"],
      incident: {
        id: "conflict-1",
        type: "duplicate_work",
        status: "open",
        filePath: "src/auth/session.ts",
        agentIds: ["agent-01", "agent-02"],
      },
    });
    expect(events.find((event) => event.id === "conflict-conflict-2")).toMatchObject({
      kind: "merge_detected",
      agentId: "agent-03",
      incident: {
        id: "conflict-2",
        type: "merge_conflict",
        status: "approved",
      },
    });
    expect(events.find((event) => event.id === "conflict-conflict-3")).toMatchObject({
      kind: "merge_detected",
      incident: {
        status: "open",
      },
    });
    expect(events.find((event) => event.id === "history-0")).toMatchObject({
      kind: "intent_declared",
      id: "history-0",
      agentId: "agent-01",
      taskTitle: "Auth session hardening",
      filePath: "src/auth/session.ts",
    });
    expect(events.find((event) => event.id === "history-1")).toMatchObject({
      kind: "guardrail_blocked",
      id: "history-1",
      agentId: "agent-07",
      incident: {
        type: "guardrail_block",
        summary: "Blocked unsafe cache invalidation",
      },
    });
  });

  it("normalizes intent history records with top-level agent IDs", async () => {
    mockedFetchConflicts.mockResolvedValue([]);
    mockedFetchHistory.mockResolvedValue([
      {
        event_type: "intent_declared",
        timestamp: "2026-05-16T17:59:00.000Z",
        agent_id: "agent-01",
        payload: {
          intent: "Auth session hardening",
          file_path: "src/auth/session.ts",
        },
      },
    ]);

    const events = await fetchLiveSessionEvents("session-1");

    expect(events.find((event) => event.id === "history-0")).toMatchObject({
      kind: "intent_declared",
      agentId: "agent-01",
      taskTitle: "Auth session hardening",
      filePath: "src/auth/session.ts",
      description: "Auth session hardening in src/auth/session.ts.",
    });
  });

  it("uses guardrail history descriptions as blocked summaries", async () => {
    mockedFetchConflicts.mockResolvedValue([]);
    mockedFetchHistory.mockResolvedValue([
      {
        event_type: "guardrail_blocked",
        timestamp: "2026-05-16T18:03:00.000Z",
        agent_id: "agent-07",
        payload: {
          action_type: "guardrail_blocked",
          file_path: "src/cache.ts",
          description: "File src/cache.ts active for agents: agent-01",
        },
      },
    ]);

    const events = await fetchLiveSessionEvents("session-1");

    expect(events.find((event) => event.id === "history-0")).toMatchObject({
      kind: "guardrail_blocked",
      agentId: "agent-07",
      description: "File src/cache.ts active for agents: agent-01",
      incident: {
        type: "guardrail_block",
        summary: "File src/cache.ts active for agents: agent-01",
        filePath: "src/cache.ts",
      },
    });
  });

  it("emits placeholder agent starts for live conflicts and supported history", async () => {
    mockedFetchConflicts.mockResolvedValue([
      {
        conflict_id: "conflict-1",
        session_id: "session-1",
        file_path: "src/auth/session.ts",
        status: "pending_approval",
        conflict_type: "duplicate_work",
        created_at: "2026-05-16T18:00:00.000Z",
        agent_a_id: "agent-01",
        agent_b_id: "agent-02",
      },
    ]);
    mockedFetchHistory.mockResolvedValue([
      {
        event_type: "intent_declared",
        created_at: "2026-05-16T17:59:00.000Z",
        payload: {
          agent_id: "agent-01",
          task_title: "Auth session hardening",
          file_path: "src/auth/session.ts",
        },
      },
    ]);

    const events = await fetchLiveSessionEvents("session-1");
    const agentStarts = events.filter((event) => event.kind === "agent_started");

    expect(agentStarts).toHaveLength(2);
    expect(agentStarts).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "agent-started-agent-01",
          agent: expect.objectContaining({
            id: "agent-01",
            name: "agent-01",
            taskTitle: "Auth session hardening",
            filePath: "src/auth/session.ts",
          }),
        }),
        expect.objectContaining({
          id: "agent-started-agent-02",
          agent: expect.objectContaining({
            id: "agent-02",
            name: "agent-02",
            filePath: "src/auth/session.ts",
          }),
        }),
      ]),
    );
    expect(events.find((event) => event.kind === "duplicate_detected")).toMatchObject({
      incident: {
        id: "conflict-1",
        status: "open",
      },
    });
  });

  it("maps backend conflict statuses to incident statuses", async () => {
    mockedFetchConflicts.mockResolvedValue([
      {
        conflict_id: "pending-conflict",
        session_id: "session-1",
        file_path: "src/auth/session.ts",
        status: "pending_approval",
        conflict_type: "merge_conflict",
        created_at: "2026-05-16T18:00:00.000Z",
        agent_a_id: "agent-01",
        agent_b_id: "agent-02",
      },
      {
        conflict_id: "auto-conflict",
        session_id: "session-1",
        file_path: "src/catalog/cards.ts",
        status: "auto_applied",
        conflict_type: "merge_conflict",
        created_at: "2026-05-16T18:01:00.000Z",
        agent_a_id: "agent-03",
        agent_b_id: "agent-04",
      },
    ]);
    mockedFetchHistory.mockResolvedValue([]);

    const events = await fetchLiveSessionEvents("session-1");

    expect(events.find((event) => event.id === "conflict-pending-conflict")).toMatchObject({
      incident: { status: "open" },
    });
    expect(events.find((event) => event.id === "conflict-auto-conflict")).toMatchObject({
      incident: { status: "resolved" },
    });
  });

  it("normalizes live intent conflicts without treating them as merge conflicts", async () => {
    mockedFetchConflicts.mockResolvedValue([
      {
        conflict_id: "intent-conflict",
        session_id: "session-1",
        file_path: "src/search/query.ts",
        status: "pending_approval",
        conflict_type: "intent_conflict",
        created_at: "2026-05-16T18:02:00.000Z",
        agent_a_id: "agent-05",
        agent_b_id: "agent-06",
      },
    ]);
    mockedFetchHistory.mockResolvedValue([]);

    const events = await fetchLiveSessionEvents("session-1");

    expect(events.find((event) => event.id === "conflict-intent-conflict")).toMatchObject({
      kind: "merge_detected",
      incident: {
        id: "intent-conflict",
        type: "intent_conflict",
      },
    });
  });

  it("hydrates live conflict incidents with available resolution detail", async () => {
    mockedFetchConflicts.mockResolvedValue([
      {
        conflict_id: "duplicate-conflict",
        session_id: "session-1",
        file_path: "src/search/query.ts",
        status: "pending_approval",
        conflict_type: "duplicate_work",
        created_at: "2026-05-16T18:02:00.000Z",
        agent_a_id: "agent-05",
        agent_b_id: "agent-06",
      },
    ]);
    mockedFetchHistory.mockResolvedValue([]);
    mockedFetchConflictDetail.mockResolvedValue({
      conflict_id: "duplicate-conflict",
      session_id: "session-1",
      file_path: "src/search/query.ts",
      status: "pending_approval",
      agent_a: { agent_id: "agent-05", intent: "Improve search", code: "" },
      agent_b: { agent_id: "agent-06", intent: "Tune ranking", code: "" },
      resolution: {
        conflict_type: "duplicate_work",
        reasoning: "Both agents are editing the same ranking flow.",
        resolved_code: "export const rank = () => 'resolved';",
        tokens_saved_estimate: "1.2k",
        suggested_new_task: "Move agent-06 to analytics filters",
      },
    });

    const events = await fetchLiveSessionEvents("session-1");

    expect(fetchConflictDetail).toHaveBeenCalledWith("duplicate-conflict");
    expect(events.find((event) => event.id === "conflict-duplicate-conflict")).toMatchObject({
      incident: {
        reasoning: "Both agents are editing the same ranking flow.",
        resolvedCode: "export const rank = () => 'resolved';",
        suggestedTask: "Move agent-06 to analytics filters",
      },
    });
  });

  it("falls back to summary-only live incidents when detail hydration fails", async () => {
    mockedFetchConflicts.mockResolvedValue([
      {
        conflict_id: "merge-conflict",
        session_id: "session-1",
        file_path: "src/search/query.ts",
        status: "pending_approval",
        conflict_type: "merge_conflict",
        created_at: "2026-05-16T18:02:00.000Z",
        agent_a_id: "agent-05",
        agent_b_id: "agent-06",
      },
    ]);
    mockedFetchHistory.mockResolvedValue([]);
    mockedFetchConflictDetail.mockRejectedValue(new Error("boom"));

    const events = await fetchLiveSessionEvents("session-1");

    expect(events.find((event) => event.id === "conflict-merge-conflict")).toMatchObject({
      incident: {
        id: "merge-conflict",
        summary: "agent-05 and agent-06 require coordination for src/search/query.ts.",
      },
    });
  });

  it("normalizes conflict resolution and approval history into timeline events", async () => {
    mockedFetchConflicts.mockResolvedValue([]);
    mockedFetchHistory.mockResolvedValue([
      {
        event_type: "conflict_resolved",
        timestamp: "2026-05-16T18:04:00.000Z",
        agent_id: "agent-05",
        payload: {
          conflict_id: "conflict-1",
          file_path: "src/search/query.ts",
          summary: "Helm generated a resolution.",
        },
      },
      {
        event_type: "conflict_approved",
        timestamp: "2026-05-16T18:05:00.000Z",
        agent_id: "agent-06",
        payload: {
          conflict_id: "conflict-1",
          approved: true,
          summary: "Human approved the resolution.",
        },
      },
    ]);

    const events = await fetchLiveSessionEvents("session-1");

    expect(events.find((event) => event.id === "history-0")).toMatchObject({
      kind: "merge_resolved",
      agentId: "agent-05",
      incidentId: "conflict-1",
      description: "Helm generated a resolution.",
    });
    expect(events.find((event) => event.id === "history-1")).toMatchObject({
      kind: "human_review",
      agentId: "agent-06",
      incidentId: "conflict-1",
      description: "Human approved the resolution.",
    });
  });

  it("does not duplicate agent placeholders for repeated agent IDs", async () => {
    mockedFetchConflicts.mockResolvedValue([
      {
        conflict_id: "conflict-1",
        session_id: "session-1",
        file_path: "src/auth/session.ts",
        status: "pending_approval",
        conflict_type: "duplicate_work",
        created_at: "2026-05-16T18:00:00.000Z",
        agent_a_id: "agent-01",
        agent_b_id: "agent-02",
      },
      {
        conflict_id: "conflict-2",
        session_id: "session-1",
        file_path: "src/auth/session.ts",
        status: "pending_approval",
        conflict_type: "merge_conflict",
        created_at: "2026-05-16T18:01:00.000Z",
        agent_a_id: "agent-01",
        agent_b_id: "agent-02",
      },
    ]);
    mockedFetchHistory.mockResolvedValue([
      {
        event_type: "intent_declared",
        payload: {
          agent_id: "agent-01",
          task_title: "Auth session hardening",
        },
      },
    ]);

    const events = await fetchLiveSessionEvents("session-1");

    expect(events.filter((event) => event.id === "agent-started-agent-01")).toHaveLength(
      1,
    );
    expect(events.filter((event) => event.id === "agent-started-agent-02")).toHaveLength(
      1,
    );
  });
});
