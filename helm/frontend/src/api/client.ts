const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type ConflictSummary = {
  conflict_id: string;
  session_id: string;
  agent_a_id: string;
  agent_b_id: string;
  file_path: string;
  status: string;
  conflict_type: string;
  created_at: string;
};

export type ResolveDetail = {
  conflict_id: string;
  session_id: string;
  file_path: string;
  status: string;
  agent_a: { agent_id: string; intent: string; code: string };
  agent_b: { agent_id: string; intent: string; code: string };
  resolution: {
    conflict_type: string;
    reasoning: string;
    resolved_code: string;
    tokens_saved_estimate: string;
    duplicate_detected?: boolean;
    agent_to_continue?: string;
    agent_to_reassign?: string;
    suggested_new_task?: string;
  };
};

export async function fetchConflicts(sessionId: string, status?: string) {
  const params = new URLSearchParams({ session_id: sessionId });
  if (status) params.set("status", status);
  const response = await fetch(`${BASE}/conflicts?${params}`);
  if (!response.ok) throw new Error(await response.text());
  return (await response.json()) as ConflictSummary[];
}

export async function fetchHistory(sessionId: string) {
  const params = new URLSearchParams({ session_id: sessionId });
  const response = await fetch(`${BASE}/history?${params}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function approveConflict(conflictId: string, approved: boolean) {
  const response = await fetch(`${BASE}/conflicts/${conflictId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function fetchConflictDetail(conflictId: string): Promise<ResolveDetail> {
  const response = await fetch(`${BASE}/conflicts/${conflictId}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
