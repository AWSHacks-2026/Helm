const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type ScenarioMeta = {
  name: string;
  kind: string;
  title: string;
  description: string;
};

export type DemoResolveResult = {
  agent_a: { intent: string; code: string };
  agent_b: { intent: string; code: string };
  resolution: {
    conflict_type: string;
    reasoning: string;
    resolved_code: string;
    tokens_saved_estimate: string;
    verdict?: string;
  };
};

export type GuardrailDemoResult = {
  agent_a: { intent: string; code: string };
  agent_b: { intent: string; code: string };
  proposed_action: Record<string, unknown>;
  preflight: { allowed: boolean; rule?: string; message?: string };
  resolution: DemoResolveResult["resolution"] | null;
  executed: boolean;
};

export type SmokeCheck = {
  scenario: string;
  endpoint: string;
  passed: boolean;
  detail: string;
};

export type SmokeResult = {
  all_passed: boolean;
  mock_bedrock: boolean;
  checks: SmokeCheck[];
};

const SCENARIO_META: Record<string, Omit<ScenarioMeta, "name">> = {
  merge_conflict: {
    kind: "merge",
    title: "Act 1: Cache vs readability",
    description: "Two agents edited get_user differently.",
  },
  intent_conflict: {
    kind: "intent",
    title: "Act 2: Performance vs dependencies",
    description: "Contradictory goals before code diverges.",
  },
  guardrail_prevention: {
    kind: "guardrail",
    title: "Act 3: Block cache utility delete",
    description: "Preflight blocks delete; Helm arbitrates.",
  },
};

export function listDemoScenarios(): ScenarioMeta[] {
  return Object.entries(SCENARIO_META).map(([name, meta]) => ({
    name,
    ...meta,
  }));
}

export async function runDemoScenario(
  name: string
): Promise<DemoResolveResult | GuardrailDemoResult> {
  if (name === "guardrail_prevention") {
    const response = await fetch(`${BASE}/guardrail/check`, { method: "POST" });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }
  const response = await fetch(`${BASE}/resolve/demo/${name}`, { method: "POST" });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function runDemoSmoke(): Promise<SmokeResult> {
  const response = await fetch(`${BASE}/demo/smoke`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
