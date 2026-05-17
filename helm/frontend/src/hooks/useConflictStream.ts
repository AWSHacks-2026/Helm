import { useEffect } from "react";

export type ConflictStreamMessage =
  | { type: "connected" }
  | { type: "disconnected" }
  | { type: "message"; payload: unknown };

export function useConflictStream(
  sessionId: string,
  onEvent: (message: ConflictStreamMessage) => void,
) {
  useEffect(() => {
    if (!sessionId) return;
    let isMounted = true;
    let reconnectTimer: number | undefined;
    let ws: WebSocket | undefined;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;

    const connect = () => {
      const socket = new WebSocket(
        `${protocol}//${host}/ws/conflicts?session_id=${encodeURIComponent(sessionId)}`,
      );
      ws = socket;

      const isActiveSocket = () => isMounted && ws === socket;

      socket.onopen = () => {
        if (!isActiveSocket()) return;

        onEvent({ type: "connected" });
      };

      socket.onmessage = (event) => {
        if (!isActiveSocket()) return;

        try {
          onEvent({ type: "message", payload: JSON.parse(event.data) });
        } catch {
          onEvent({ type: "message", payload: event.data });
        }
      };

      socket.onclose = () => {
        if (!isActiveSocket()) return;

        onEvent({ type: "disconnected" });
        if (!sessionId) return;

        reconnectTimer = window.setTimeout(connect, 1000);
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [sessionId, onEvent]);
}
