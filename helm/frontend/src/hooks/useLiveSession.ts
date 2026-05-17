import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchLiveSessionEvents } from "../api/orchestration";
import { buildDashboardModel } from "../orchestration/dashboardModel";
import type { DashboardModel, TimelineEvent } from "../orchestration/types";
import { useConflictStream, type ConflictStreamMessage } from "./useConflictStream";

export type LiveConnectionStatus =
  | "idle"
  | "loading"
  | "connected"
  | "reconnecting"
  | "error";

type LiveSessionState = {
  sessionId: string;
  events: TimelineEvent[];
  status: LiveConnectionStatus;
  error: Error | null;
};

const emptyLiveDashboardModel = (): DashboardModel =>
  buildDashboardModel([], "live");

export function useLiveSession(sessionId: string): {
  model: DashboardModel;
  status: LiveConnectionStatus;
  error: Error | null;
  refresh: () => Promise<void>;
} {
  const normalizedSessionId = sessionId.trim();
  const requestIdRef = useRef(0);
  const sessionIdRef = useRef(normalizedSessionId);
  const [state, setState] = useState<LiveSessionState>({
    sessionId: normalizedSessionId,
    events: [],
    status: normalizedSessionId ? "loading" : "idle",
    error: null,
  });

  useEffect(() => {
    sessionIdRef.current = normalizedSessionId;
    requestIdRef.current += 1;
    setState((current) =>
      current.sessionId === normalizedSessionId
        ? current
        : {
            sessionId: normalizedSessionId,
            events: [],
            status: normalizedSessionId ? "loading" : "idle",
            error: null,
          },
    );
  }, [normalizedSessionId]);

  const refresh = useCallback(async () => {
    const requestSessionId = normalizedSessionId;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;

    if (!normalizedSessionId) {
      setState({ sessionId: "", events: [], status: "idle", error: null });
      return;
    }

    setState((current) => {
      const isSameSession = current.sessionId === requestSessionId;

      return {
        ...current,
        sessionId: requestSessionId,
        events: isSameSession ? current.events : [],
        status:
          isSameSession &&
          (current.status === "connected" || current.status === "reconnecting")
            ? current.status
            : "loading",
        error: null,
      };
    });

    try {
      const events = await fetchLiveSessionEvents(requestSessionId);
      if (
        requestId !== requestIdRef.current ||
        requestSessionId !== sessionIdRef.current
      ) {
        return;
      }

      setState((current) => ({
        sessionId: requestSessionId,
        events,
        status: current.status === "reconnecting" ? "reconnecting" : "connected",
        error: null,
      }));
    } catch (err) {
      if (
        requestId !== requestIdRef.current ||
        requestSessionId !== sessionIdRef.current
      ) {
        return;
      }

      setState((current) => ({
        ...current,
        sessionId: requestSessionId,
        events: current.sessionId === requestSessionId ? current.events : [],
        status: "error",
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [normalizedSessionId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useConflictStream(
    normalizedSessionId,
    useCallback(
      (message: ConflictStreamMessage) => {
        if (!normalizedSessionId) return;

        if (message.type === "connected") {
          setState((current) => ({ ...current, status: "connected" }));
          return;
        }

        if (message.type === "disconnected") {
          setState((current) => ({
            ...current,
            status: current.status === "error" ? "error" : "reconnecting",
          }));
          return;
        }

        void refresh();
      },
      [normalizedSessionId, refresh],
    ),
  );

  const model = useMemo(
    () =>
      normalizedSessionId && state.sessionId === normalizedSessionId
        ? buildDashboardModel(state.events, "live")
        : emptyLiveDashboardModel(),
    [normalizedSessionId, state.events, state.sessionId],
  );

  return {
    model,
    status:
      normalizedSessionId && state.sessionId === normalizedSessionId
        ? state.status
        : normalizedSessionId
          ? "loading"
          : "idle",
    error:
      normalizedSessionId && state.sessionId === normalizedSessionId
        ? state.error
        : null,
    refresh,
  };
}
