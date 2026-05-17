/** Judge-facing names for demo agents (IDs stay agent_a for API/replay). */
export const AGENT_DISPLAY_NAMES: Record<string, string> = {
  agent_a: "Ravi",
  agent_b: "Priya",
  agent_c: "Jordan",
  agent_d: "Sam",
  agent_e: "Taylor",
  agent_f: "Casey",
};

export function formatAgentName(agentId: string): string {
  return (
    AGENT_DISPLAY_NAMES[agentId] ??
    agentId.replace(/^agent_/, "").replace(/_/g, " ")
  );
}

export function formatAgentIdList(agentIds: string[]): string {
  return agentIds.map(formatAgentName).join(", ");
}

/** Replace agent_a-style IDs in timeline copy with first names. */
export function humanizeAgentText(text: string): string {
  return Object.entries(AGENT_DISPLAY_NAMES).reduce(
    (result, [id, name]) => result.replaceAll(id, name),
    text,
  );
}
