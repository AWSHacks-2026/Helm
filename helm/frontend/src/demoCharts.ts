/** ShopFix live AWS benchmark charts (served from /demo-charts/). */

export type DemoChart = {
  id: string;
  src: string;
  title: string;
  pillar: "overview" | "contention" | "merge" | "guardrails";
  caption: string;
  featured?: boolean;
};

export const DEMO_CHARTS: DemoChart[] = [
  {
    id: "dashboard",
    src: "/demo-charts/00_dashboard.png",
    title: "Four pillars at a glance",
    pillar: "overview",
    caption:
      "Contention gate, parallel merge fleet, and ShopFix guardrails — live AWS ShopFix runs (intent opposition excluded).",
    featured: true,
  },
  {
    id: "contention-savings",
    src: "/demo-charts/01_contention_savings.png",
    title: "Contention: cost & wall savings",
    pillar: "contention",
    caption:
      "Helm trims duplicate agent work before edits. At N=8 agents, ~+18% cost and ~+39% wall vs baseline with 6 agents running.",
  },
  {
    id: "contention-agents",
    src: "/demo-charts/03_contention_agents.png",
    title: "Contention: fewer agents run",
    pillar: "contention",
    caption: "Dedup + trim means not every agent burns a full Haiku implementation on the same file.",
  },
  {
    id: "merge-fleet",
    src: "/demo-charts/04_merge_fleet_wall.png",
    title: "Merge fleet: parallel conflict resolution",
    pillar: "merge",
    caption:
      "Per-file merge in parallel vs sequential chain. Sweet spot around N=6 contested files on ShopFix merge-heavy suite.",
  },
  {
    id: "guardrail-headline",
    src: "/demo-charts/09_guardrail_headline.png",
    title: "Guardrails: block before write",
    pillar: "guardrails",
    caption:
      "ShopFix auth.py — baseline runs destructive edit twice; Helm guardrail blocks once (~45% cost, ~55% wall median vs 2× Haiku).",
  },
];

export const FEATURED_DEMO_CHART =
  DEMO_CHARTS.find((chart) => chart.featured) ?? DEMO_CHARTS[0];

export const PILLAR_DEMO_CHARTS = DEMO_CHARTS.filter((chart) => !chart.featured);

export const ALL_DEMO_CHARTS = [FEATURED_DEMO_CHART, ...PILLAR_DEMO_CHARTS];
