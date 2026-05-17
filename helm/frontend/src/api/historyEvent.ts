const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export async function postHistoryEvent(
  sessionId: string,
  eventType: string,
  payload: Record<string, unknown>,
): Promise<void> {
  const response = await fetch(`${BASE}/history/event`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      event_type: eventType,
      payload,
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }

  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("helm-ledger-updated"));
  }
}
