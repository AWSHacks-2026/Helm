import type { AppView } from "./components/AppShell";

export type WalkthroughStep = {
  id: string;
  view: Extract<AppView, "control" | "incidents" | "gratitude" | "proof">;
  title: string;
  instruction: string;
  selectIncidentType?: "duplicate_work" | "guardrail_block";
};

export const JUDGE_WALKTHROUGH: WalkthroughStep[] = [
  {
    id: "replay",
    view: "control",
    title: "Fleet coordination in motion",
    instruction:
      "Watch Overlord on ShopFix: dedup on auth.py before agents pile on, a guardrail block that prevents a destructive rewrite, reassignments instead of wasted Haiku runs.",
  },
  {
    id: "incident",
    view: "incidents",
    title: "Duplicate work stopped early",
    instruction:
      "This is the grind our parents lived — two agents, one file. Open the incident: gate decision, reasoning, and who got sent to new work.",
    selectIncidentType: "duplicate_work",
  },
  {
    id: "gratitude",
    view: "gratitude",
    title: "Build with Gratitude",
    instruction:
      "The ledger is the theme made visible: blocked writes, deduped missions, tokens not burned. Every metric is time back for someone still in the chair.",
  },
  {
    id: "proof",
    view: "proof",
    title: "Measured on Amazon Bedrock",
    instruction:
      "Four pillars from live ShopFix benchmarks — not slide-ware. Use ← → on the chart deck; contention gate, dedup, merge fleet, guardrails.",
  },
];
