import type { TimelineEvent } from "../orchestration/types";
import { getSnippet, type SnippetKey } from "./snippets";
import { buildTraceEdges } from "./traceEdges";
import type {
  TraceAgentState,
  TraceFileState,
  TraceFrame,
  TraceHelmState,
} from "./types";

export type TraceSnippetRole =
  | "clean"
  | "edit_a"
  | "edit_b"
  | "conflict"
  | "merged"
  | "blocked";

export type TraceSnippetMap = Record<TraceSnippetRole, SnippetKey>;

export type BuildTraceOptions = {
  primaryFile: string;
  agentIds: [string, string];
  snippets: TraceSnippetMap;
};

const msBetween = (events: TimelineEvent[]): number[] => {
  if (events.length === 0) {
    return [];
  }
  const t0 = Date.parse(events[0].timestamp);
  return events.map((event) => Math.max(0, Date.parse(event.timestamp) - t0));
};

const defaultAgents = (
  agentIds: [string, string],
  filePath: string,
): TraceAgentState[] => [
  { id: agentIds[0], status: "idle", taskTitle: "—", filePath },
  { id: agentIds[1], status: "idle", taskTitle: "—", filePath },
];

export function buildTraceFrames(
  events: TimelineEvent[],
  options: BuildTraceOptions,
): TraceFrame[] {
  const sorted = [...events].sort(
    (left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp),
  );
  const offsets = msBetween(sorted);
  const [agentA, agentB] = options.agentIds;
  const file = options.primaryFile;
  const snippets = options.snippets;

  let agents = defaultAgents(options.agentIds, file);
  let helm: TraceHelmState = { active: false };
  let snippetKey: SnippetKey = snippets.clean;
  let fileStatus: TraceFileState["status"] = "clean";

  const frames: TraceFrame[] = [];

  for (let index = 0; index < sorted.length; index++) {
    const event = sorted[index];
    helm = { active: false };

    switch (event.kind) {
      case "agent_started":
        agents = agents.map((agent) =>
          agent.id === event.agent.id
            ? {
                ...agent,
                status: "coding",
                taskTitle: event.agent.taskTitle,
                filePath: event.agent.filePath ?? file,
              }
            : agent,
        );
        snippetKey =
          event.agent.id === agentA ? snippets.edit_a : snippets.edit_b;
        fileStatus = "editing";
        break;
      case "intent_declared":
        agents = agents.map((agent) =>
          agent.id === event.agentId
            ? {
                ...agent,
                status: "coding",
                taskTitle: event.taskTitle,
                filePath: event.filePath ?? file,
              }
            : agent,
        );
        if (event.agentId === agentA) {
          snippetKey = snippets.edit_a;
        } else if (event.agentId === agentB) {
          snippetKey = snippets.edit_b;
        }
        fileStatus = "editing";
        break;
      case "duplicate_detected":
        helm = { active: true, action: "dedup", detail: event.description };
        agents = agents.map((agent) =>
          event.blockedAgentIds?.includes(agent.id)
            ? { ...agent, status: "blocked" }
            : { ...agent, status: "coding" },
        );
        fileStatus = "editing";
        break;
      case "agent_reassigned":
        agents = agents.map((agent) =>
          agent.id === event.agentId
            ? {
                ...agent,
                status: "reassigned",
                taskTitle: event.taskTitle,
                filePath: event.filePath ?? file,
              }
            : agent,
        );
        helm = { active: true, action: "reassign", detail: event.taskTitle };
        break;
      case "guardrail_blocked":
        helm = { active: true, action: "guardrail", detail: event.description };
        agents = agents.map((agent) =>
          agent.id === event.agentId ? { ...agent, status: "blocked" } : agent,
        );
        snippetKey = snippets.blocked;
        fileStatus = "blocked";
        break;
      case "merge_detected":
        helm = { active: true, action: "merge", detail: "Conflict detected" };
        snippetKey = snippets.conflict;
        fileStatus = "conflict";
        agents = agents.map((agent) => ({ ...agent, status: "conflicted" }));
        break;
      case "merge_resolved":
        helm = { active: true, action: "merge", detail: event.description };
        snippetKey = snippets.merged;
        fileStatus = "merged";
        agents = agents.map((agent) => ({ ...agent, status: "complete" }));
        break;
      default:
        break;
    }

    const agentSnapshot = agents.map((agent) => ({ ...agent }));
    const helmSnapshot = { ...helm };
    frames.push({
      id: `frame-${event.id}`,
      atMs: offsets[index] ?? index * 1200,
      title: event.title,
      narration: event.description,
      agents: agentSnapshot,
      helm: helmSnapshot,
      edges: buildTraceEdges(agentSnapshot, helmSnapshot),
      files: [
        {
          path: file,
          status: fileStatus,
          snippet: getSnippet(snippetKey),
        },
      ],
      sourceEventId: event.id,
    });
  }

  return frames;
}
