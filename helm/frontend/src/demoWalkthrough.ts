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
      "Watch Helm on ShopFix: dedup on auth.py before agents pile on, a guardrail that blocks a bad rewrite, and reassignments instead of wasted Haiku runs.",
  },
  {
    id: "incident",
    view: "incidents",
    title: "Duplicate work stopped early",
    instruction:
      "Two agents, one file. That is the grind our parents knew. Open the incident for the gate call, the reasoning, and who got new work.",
    selectIncidentType: "duplicate_work",
  },
  {
    id: "gratitude",
    view: "gratitude",
    title: "Build with Gratitude",
    instruction:
      "The ledger is the theme on screen: blocked writes, deduped missions, tokens you did not burn. Each metric is time back for someone still at the keyboard.",
  },
  {
    id: "proof",
    view: "proof",
    title: "Measured on Amazon Bedrock",
    instruction:
      "Four pillars from live ShopFix runs, not slide-ware. Use the arrow keys on the chart deck: gate, dedup, merge fleet, guardrails.",
  },
];
