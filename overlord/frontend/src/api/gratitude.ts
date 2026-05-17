const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type GratitudeLedger = {
  intents_declared: number;
  guardrails_blocked: number;
  intents_aligned: number;
  duplicates_avoided: number;
  agents_yielded: number;
  tokens_saved_total: number;
  tokens_saved_display: string;
  haiku_calls: number;
  sonnet_calls: number;
  timeline: { kind: string; message: string; at?: string }[];
};

export async function fetchGratitude(sessionId: string): Promise<GratitudeLedger> {
  const response = await fetch(
    `${BASE}/gratitude?session_id=${encodeURIComponent(sessionId)}`
  );
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
