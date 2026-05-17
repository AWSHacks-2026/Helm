import type { FlightTrace, TraceScenario } from "./types";
import { loadContentionN2Trace } from "./traces/contentionN2";
import {
  loadLiveContentionN2BaselineTrace,
  loadLiveContentionN2HelmTrace,
} from "./traces/liveContentionN2";
import { loadMergeN2Trace } from "./traces/mergeConflictN2";

export type TraceScenarioId =
  | "contention_n2"
  | "contention_n2_live_helm"
  | "contention_n2_live_baseline"
  | "merge_n2";

export interface TraceScenarioEntry {
  id: TraceScenarioId;
  label: string;
  description: string;
  load: () => FlightTrace | Promise<FlightTrace>;
}

export const TRACE_SCENARIOS: TraceScenarioEntry[] = [
  {
    id: "contention_n2_live_helm",
    label: "Live · Helm path (Bedrock)",
    description:
      "Real matrix run — Helm guardrails, continuations, measured savings vs baseline.",
    load: loadLiveContentionN2HelmTrace,
  },
  {
    id: "contention_n2_live_baseline",
    label: "Live · Baseline path (Bedrock)",
    description:
      "Same fixture without Helm API — agents collide, Haiku merge-fix on auth.py.",
    load: loadLiveContentionN2BaselineTrace,
  },
  {
    id: "contention_n2",
    label: "N=2 · Fleet dedup (auth.py)",
    description: "Two agents overlap on auth.py — Helm dedupes and reassigns.",
    load: loadContentionN2Trace,
  },
  {
    id: "merge_n2",
    label: "N=2 · Merge conflict (cart.py)",
    description: "Two agents collide on checkout_total — Helm merges.",
    load: loadMergeN2Trace,
  },
];

export function getTraceScenario(id: string): TraceScenarioEntry {
  return TRACE_SCENARIOS.find((scenario) => scenario.id === id) ?? TRACE_SCENARIOS[0];
}
