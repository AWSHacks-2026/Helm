export type DemoPillarId = "gate" | "contention" | "merge" | "guardrails";

export type DemoPillar = {
  id: DemoPillarId;
  label: string;
  headline: string;
  subline: string;
  costSavingsPct?: number;
  wallSavingsPct?: number;
  awsServices: string[];
  liveCommand: string;
};

/** Source: experiments/SHOPFIX_DEMO_PREP.md + shopfix_demo_matrix_20260517_091231.json */
export const DEMO_PILLARS: DemoPillar[] = [
  {
    id: "gate",
    label: "Contention gate",
    headline: "0 dedup Bedrock calls when work is disjoint",
    subline: "Six agents, six files — gate allow, same cost as baseline.",
    awsServices: ["Bedrock Haiku", "Rule preflight"],
    liveCommand: "python scripts/run_shopfix_live_benchmark.py --suite disjoint --agents 6",
  },
  {
    id: "contention",
    label: "Duplicate work",
    headline: "N=8: +18% cost, +39% wall — 6 agents not 8",
    subline: "Dedup + trim before Haiku edits on ShopFix contention suite.",
    costSavingsPct: 18,
    wallSavingsPct: 39,
    awsServices: ["Bedrock Haiku", "Fleet dedup"],
    liveCommand:
      "python scripts/run_shopfix_live_benchmark.py --suite contention --agents 8",
  },
  {
    id: "merge",
    label: "Merge fleet",
    headline: "N=6: +30% merge-phase wall on 2 contested files",
    subline: "Parallel per-file merge-fix vs sequential chain (Haiku).",
    wallSavingsPct: 30,
    awsServices: ["Bedrock Haiku"],
    liveCommand:
      "python scripts/run_shopfix_merge_fleet_benchmark.py contention 6",
  },
  {
    id: "guardrails",
    label: "Guardrails",
    headline: "ShopFix auth.py: +45% cost, +55% wall vs 2× destructive edit",
    subline: "Block delete before write — 1 guardrail call vs 2 rebuild edits.",
    costSavingsPct: 45,
    wallSavingsPct: 55,
    awsServices: ["Bedrock Haiku", "Knowledge base rules"],
    liveCommand: "python scripts/run_shopfix_guardrail_benchmark.py",
  },
];

export const pillarById = (id: DemoPillarId): DemoPillar | undefined =>
  DEMO_PILLARS.find((pillar) => pillar.id === id);
