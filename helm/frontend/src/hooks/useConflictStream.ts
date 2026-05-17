import { useEffect } from "react";

export function useConflictStream(
  sessionId: string,
  onEvent: (message: unknown) => void
) {
  useEffect(() => {
    if (!sessionId) return;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const ws = new WebSocket(
      `${protocol}//${host}/ws/conflicts?session_id=${encodeURIComponent(sessionId)}`
    );
    ws.onmessage = (event) => {
      try {
        onEvent(JSON.parse(event.data));
      } catch {
        onEvent(event.data);
      }
    };
    return () => ws.close();
  }, [sessionId, onEvent]);
}
