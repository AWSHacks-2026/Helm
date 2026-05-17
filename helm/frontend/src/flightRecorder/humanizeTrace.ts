import { humanizeAgentText } from "../content/agentPersonas";
import type { FlightTrace } from "./types";

export function humanizeTrace(trace: FlightTrace): FlightTrace {
  return {
    ...trace,
    description: humanizeAgentText(trace.description),
    frames: trace.frames.map((frame) => ({
      ...frame,
      title: humanizeAgentText(frame.title),
      narration: humanizeAgentText(frame.narration),
      helm: frame.helm.detail
        ? { ...frame.helm, detail: humanizeAgentText(frame.helm.detail) }
        : frame.helm,
    })),
  };
}
