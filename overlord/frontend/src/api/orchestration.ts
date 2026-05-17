import {
  fetchConflictDetail,
  fetchConflicts,
  fetchHistory,
  type ConflictSummary,
  type ResolveDetail,
} from "./client";
import type { AgentState, IncidentState, TimelineEvent } from "../orchestration/types";

type JsonRecord = Record<string, unknown>;
type AgentHint = {
  id: string;
  timestamp: string;
  taskTitle?: string;
  filePath?: string;
};

const isRecord = (value: unknown): value is JsonRecord =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const stringValue = (value: unknown): string | undefined =>
  typeof value === "string" && value.length > 0 ? value : undefined;

const firstString = (...values: unknown[]): string | undefined => {
  for (const value of values) {
    const text = stringValue(value);
    if (text) return text;
  }

  return undefined;
};

const incidentStatus = (status: string): IncidentState["status"] => {
  if (status === "pending_approval") return "open";
  if (status === "auto_applied") return "resolved";
  if (status === "approved" || status === "rejected") return status;

  return "open";
};

const conflictIncidentType = (
  conflictType: string,
): IncidentState["type"] =>
  conflictType === "duplicate_work" || conflictType === "intent_conflict"
    ? conflictType
    : "merge_conflict";

const titleForConflict = (conflict: ConflictSummary): string =>
  conflict.conflict_type === "duplicate_work"
    ? `Duplicate work detected in ${conflict.file_path}`
    : `Merge conflict detected in ${conflict.file_path}`;

const hydrateIncident = (
  incident: IncidentState,
  detail: ResolveDetail | undefined,
): IncidentState => {
  if (!detail) return incident;

  return {
    ...incident,
    reasoning: detail.resolution.reasoning,
    resolvedCode: detail.resolution.resolved_code,
    suggestedTask: detail.resolution.suggested_new_task,
  };
};

const normalizeConflict = (
  conflict: ConflictSummary,
  detail?: ResolveDetail,
): TimelineEvent => {
  const agentIds = [conflict.agent_a_id, conflict.agent_b_id].filter(Boolean);
  const incident = hydrateIncident(
    {
      id: conflict.conflict_id,
      type: conflictIncidentType(conflict.conflict_type),
      status: incidentStatus(conflict.status),
      title: titleForConflict(conflict),
      summary:
        conflict.conflict_type === "duplicate_work"
          ? `${agentIds.join(" and ")} have overlapping work in ${conflict.file_path}.`
          : `${agentIds.join(" and ")} require coordination for ${conflict.file_path}.`,
      filePath: conflict.file_path,
      agentIds,
      createdAt: conflict.created_at,
    },
    detail,
  );

  if (conflict.conflict_type === "duplicate_work") {
    return {
      id: `conflict-${conflict.conflict_id}`,
      timestamp: conflict.created_at,
      kind: "duplicate_detected",
      title: incident.title,
      description: incident.summary,
      agentIds,
      blockedAgentIds: agentIds.slice(1),
      incident,
    };
  }

  return {
    id: `conflict-${conflict.conflict_id}`,
    timestamp: conflict.created_at,
    kind: "merge_detected",
    title: incident.title,
    description: incident.summary,
    agentId: conflict.agent_a_id,
    incident,
  };
};

const getPayload = (entry: JsonRecord): JsonRecord =>
  isRecord(entry.payload) ? entry.payload : {};

const getTimestamp = (entry: JsonRecord, payload: JsonRecord): string =>
  firstString(
    entry.created_at,
    entry.createdAt,
    entry.timestamp,
    payload.created_at,
    payload.createdAt,
    payload.timestamp,
  ) ?? new Date(0).toISOString();

const normalizeIntentDeclared = (
  id: string,
  entry: JsonRecord,
): TimelineEvent | null => {
  const payload = getPayload(entry);
  const agentId = firstString(payload.agent_id, payload.agentId, entry.agent_id);

  if (!agentId) return null;

  const taskTitle =
    firstString(
      payload.task_title,
      payload.taskTitle,
      payload.intent,
      payload.summary,
      entry.summary,
    ) ?? "Declared intent";
  const filePath = firstString(payload.file_path, payload.filePath, entry.file_path);

  return {
    id,
    timestamp: getTimestamp(entry, payload),
    kind: "intent_declared",
    title: `${agentId} declared intent`,
    description: filePath ? `${taskTitle} in ${filePath}.` : taskTitle,
    agentId,
    taskTitle,
    filePath,
  };
};

const normalizeGuardrailBlocked = (
  id: string,
  entry: JsonRecord,
): TimelineEvent | null => {
  const payload = getPayload(entry);
  const agentId = firstString(payload.agent_id, payload.agentId, entry.agent_id);

  if (!agentId) return null;

  const timestamp = getTimestamp(entry, payload);
  const summary =
    firstString(
      payload.summary,
      payload.reason,
      payload.description,
      payload.message,
      entry.summary,
    ) ??
    "Guardrail blocked an unsafe agent action.";
  const filePath = firstString(payload.file_path, payload.filePath, entry.file_path);
  const incident: IncidentState = {
    id: `${id}-incident`,
    type: "guardrail_block",
    status: "blocked",
    title: `${agentId} blocked by guardrail`,
    summary,
    filePath,
    agentIds: [agentId],
    createdAt: timestamp,
  };

  return {
    id,
    timestamp,
    kind: "guardrail_blocked",
    title: incident.title,
    description: summary,
    agentId,
    incident,
  };
};

const normalizeConflictResolved = (
  id: string,
  entry: JsonRecord,
): TimelineEvent => {
  const payload = getPayload(entry);
  const agentId = firstString(payload.agent_id, payload.agentId, entry.agent_id);
  const incidentId = firstString(
    payload.conflict_id,
    payload.conflictId,
    entry.conflict_id,
  );
  const description =
    firstString(
      payload.summary,
      payload.reasoning,
      payload.description,
      entry.summary,
    ) ?? "Overlord resolved a conflict.";

  return {
    id,
    timestamp: getTimestamp(entry, payload),
    kind: "merge_resolved",
    title: "Conflict resolved",
    description,
    agentId,
    incidentId,
  };
};

const normalizeConflictApproved = (
  id: string,
  entry: JsonRecord,
): TimelineEvent => {
  const payload = getPayload(entry);
  const agentId = firstString(payload.agent_id, payload.agentId, entry.agent_id);
  const incidentId = firstString(
    payload.conflict_id,
    payload.conflictId,
    entry.conflict_id,
  );
  const description =
    firstString(payload.summary, payload.description, payload.reason, entry.summary) ??
    "Human reviewed a conflict resolution.";

  return {
    id,
    timestamp: getTimestamp(entry, payload),
    kind: "human_review",
    title: "Human reviewed conflict",
    description,
    agentId,
    incidentId,
  };
};

const normalizeHistoryEntry = (
  entry: unknown,
  index: number,
): TimelineEvent | null => {
  if (!isRecord(entry)) return null;

  const eventType = firstString(entry.event_type, entry.eventType, entry.type);
  const id = `history-${index}`;

  if (eventType === "intent_declared") {
    return normalizeIntentDeclared(id, entry);
  }

  if (eventType === "guardrail_blocked") {
    return normalizeGuardrailBlocked(id, entry);
  }

  if (eventType === "conflict_resolved") {
    return normalizeConflictResolved(id, entry);
  }

  if (eventType === "conflict_approved") {
    return normalizeConflictApproved(id, entry);
  }

  return null;
};

const historyEntries = (history: unknown): unknown[] =>
  Array.isArray(history)
    ? history
    : isRecord(history) && Array.isArray(history.events)
      ? history.events
      : [];

const defaultTaskTitle = (agentId: string, filePath?: string): string =>
  filePath ? `Work in ${filePath}` : `Live activity for ${agentId}`;

const addAgentHint = (
  hints: Map<string, AgentHint>,
  nextHint: AgentHint,
): void => {
  const currentHint = hints.get(nextHint.id);

  if (!currentHint) {
    hints.set(nextHint.id, nextHint);
    return;
  }

  hints.set(nextHint.id, {
    id: nextHint.id,
    timestamp:
      Date.parse(nextHint.timestamp) < Date.parse(currentHint.timestamp)
        ? nextHint.timestamp
        : currentHint.timestamp,
    taskTitle: nextHint.taskTitle ?? currentHint.taskTitle,
    filePath: nextHint.filePath ?? currentHint.filePath,
  });
};

const addIncidentAgentHints = (
  hints: Map<string, AgentHint>,
  incident: IncidentState,
  timestamp: string,
): void => {
  for (const agentId of incident.agentIds) {
    addAgentHint(hints, {
      id: agentId,
      timestamp,
      taskTitle: defaultTaskTitle(agentId, incident.filePath),
      filePath: incident.filePath,
    });
  }
};

const collectAgentHints = (events: TimelineEvent[]): AgentHint[] => {
  const hints = new Map<string, AgentHint>();

  for (const event of events) {
    if (event.kind === "agent_started") {
      addAgentHint(hints, {
        id: event.agent.id,
        timestamp: event.timestamp,
        taskTitle: event.agent.taskTitle,
        filePath: event.agent.filePath,
      });
    }

    if (event.kind === "intent_declared") {
      addAgentHint(hints, {
        id: event.agentId,
        timestamp: event.timestamp,
        taskTitle: event.taskTitle,
        filePath: event.filePath,
      });
    }

    if (event.kind === "guardrail_blocked") {
      if (event.incident) {
        addIncidentAgentHints(hints, event.incident, event.timestamp);
      } else {
        addAgentHint(hints, {
          id: event.agentId,
          timestamp: event.timestamp,
        });
      }
    }

    if (event.kind === "merge_detected") {
      if (event.incident) {
        addIncidentAgentHints(hints, event.incident, event.timestamp);
      } else {
        addAgentHint(hints, {
          id: event.agentId,
          timestamp: event.timestamp,
        });
      }
    }

    if (event.kind === "duplicate_detected") {
      if (event.incident) {
        addIncidentAgentHints(hints, event.incident, event.timestamp);
      } else {
        for (const agentId of event.agentIds) {
          addAgentHint(hints, {
            id: agentId,
            timestamp: event.timestamp,
          });
        }
      }
    }

    if (
      (event.kind === "merge_resolved" || event.kind === "human_review") &&
      event.agentId
    ) {
      addAgentHint(hints, {
        id: event.agentId,
        timestamp: event.timestamp,
      });
    }
  }

  return [...hints.values()];
};

const placeholderAgentStartedEvents = (
  events: TimelineEvent[],
): TimelineEvent[] => {
  const existingAgentIds = new Set(
    events
      .filter((event) => event.kind === "agent_started")
      .map((event) => event.agent.id),
  );

  return collectAgentHints(events)
    .filter((hint) => !existingAgentIds.has(hint.id))
    .map((hint) => {
      const agent: AgentState = {
        id: hint.id,
        name: hint.id,
        status: "coding",
        taskTitle: hint.taskTitle ?? defaultTaskTitle(hint.id, hint.filePath),
        filePath: hint.filePath,
      };

      return {
        id: `agent-started-${hint.id}`,
        timestamp: hint.timestamp,
        kind: "agent_started",
        title: `${hint.id} joined live session`,
        description: `${hint.id} is active in the live session.`,
        agent,
      };
    });
};

export async function fetchLiveSessionEvents(
  sessionId: string,
): Promise<TimelineEvent[]> {
  const [conflicts, history] = await Promise.all([
    fetchConflicts(sessionId),
    fetchHistory(sessionId),
  ]);

  const conflictEvents = await Promise.all(
    conflicts.map(async (conflict) => {
      try {
        return normalizeConflict(
          conflict,
          await fetchConflictDetail(conflict.conflict_id),
        );
      } catch {
        return normalizeConflict(conflict);
      }
    }),
  );

  const timelineEvents: TimelineEvent[] = [
    ...conflictEvents,
    ...historyEntries(history)
      .map(normalizeHistoryEntry)
      .filter((event): event is TimelineEvent => event !== null),
  ];

  return [...placeholderAgentStartedEvents(timelineEvents), ...timelineEvents];
}
