import { createGuardrailReplayEvents } from "./guardrailReplay";
import { createMergeConflictReplayEvents } from "./mergeConflictReplay";
import { createShopfixDemoReplayEvents } from "./shopfixDemoReplay";
import type { TimelineEvent } from "./types";

export type DemoScenarioId = "fleet_contention" | "merge_conflict" | "guardrail_block";

export interface DemoScenario {
  id: DemoScenarioId;
  label: string;
  subtitle: string;
  completeHint: string;
  createEvents: () => TimelineEvent[];
}

export const DEFAULT_DEMO_SCENARIO_ID: DemoScenarioId = "fleet_contention";

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "fleet_contention",
    label: "Fleet dedup",
    subtitle:
      "ShopFix fleet: overlapping auth.py trimmed, guardrail block, contention benchmark.",
    completeHint:
      "Replay complete · open Incidents for auth.py dedup or Results for charts.",
    createEvents: createShopfixDemoReplayEvents,
  },
  {
    id: "merge_conflict",
    label: "Merge conflict",
    subtitle:
      "ShopFix cart.py: two agents collide on checkout_total(). Helm resolves with Sonnet.",
    completeHint:
      "Replay complete · open Incidents for cart.py merge detail or Results for merge benchmarks.",
    createEvents: createMergeConflictReplayEvents,
  },
  {
    id: "guardrail_block",
    label: "Guardrail",
    subtitle:
      "ShopFix auth.py: destructive session delete blocked before write. Agent yielded to disjoint file.",
    completeHint:
      "Replay complete · open Incidents for the guardrail block or Gratitude for tokens returned.",
    createEvents: createGuardrailReplayEvents,
  },
];

const scenarioById = new Map(DEMO_SCENARIOS.map((scenario) => [scenario.id, scenario]));

export const getDemoScenario = (id: DemoScenarioId): DemoScenario =>
  scenarioById.get(id) ?? DEMO_SCENARIOS[0];

export const createDemoReplayEventsForScenario = (id: DemoScenarioId): TimelineEvent[] =>
  getDemoScenario(id).createEvents();
