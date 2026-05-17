import type { FlightTrace } from "../types";

async function fetchTrace(url: string): Promise<FlightTrace> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load live trace: ${response.status} ${url}`);
  }
  const trace = (await response.json()) as FlightTrace;
  if (!trace.frames?.length || !trace.frames[0]?.edges) {
    throw new Error(`Live trace JSON missing frames or edges: ${url}`);
  }
  return trace;
}

export async function loadLiveContentionN2HelmTrace(): Promise<FlightTrace> {
  return fetchTrace("/traces/contention-n2-live.json");
}

export async function loadLiveContentionN2BaselineTrace(): Promise<FlightTrace> {
  return fetchTrace("/traces/contention-n2-live-baseline.json");
}

/** @deprecated Use loadLiveContentionN2HelmTrace */
export async function loadLiveContentionN2Trace(): Promise<FlightTrace> {
  return loadLiveContentionN2HelmTrace();
}
