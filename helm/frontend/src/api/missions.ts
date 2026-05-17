const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type MissionSummary = {
  mission_id: string;
  session_id: string;
  external_id: string | null;
  source: string;
  title: string;
  file_path: string;
  status: string;
  assigned_agent_id: string | null;
  suggested_task: string | null;
  created_at: string;
  updated_at: string;
};

export async function fetchMissions(sessionId: string) {
  const params = new URLSearchParams({ session_id: sessionId });
  const res = await fetch(`${BASE}/missions?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as MissionSummary[];
}

export async function delegateMissions(sessionId: string) {
  const res = await fetch(`${BASE}/missions/delegate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, use_llm_dedup: true }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startMission(
  missionId: string,
  sessionId: string,
  agentId?: string
) {
  const params = new URLSearchParams({ session_id: sessionId });
  const res = await fetch(`${BASE}/missions/${missionId}/start?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id: agentId ?? null }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
