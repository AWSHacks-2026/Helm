const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type MergeScenarioMeta = {
  name: string;
  kind: string;
  title: string;
  description: string;
};

export type MergeEvaluation = {
  passed: boolean;
  score: number;
  checks: Record<string, boolean>;
};

export type StrategyResult = {
  strategy: string;
  resolved_code: string;
  reasoning: string;
  elapsed_ms: number;
  evaluation: MergeEvaluation;
  conflict_type?: string;
  tokens_saved_estimate?: string;
};

export type CompareResult = {
  scenario: string;
  file_path: string;
  mock_bedrock: boolean;
  agent_a: { intent: string; code: string };
  agent_b: { intent: string; code: string };
  results: StrategyResult[];
  summary: {
    overlord_passed: boolean;
    overlord_score: number;
    best_naive_strategy: string;
    best_naive_score: number;
    overlord_beats_naive: boolean;
    score_delta: number;
  };
  mcp_hint: {
    tool: string;
    session_id: string;
    file_path: string;
  };
};

export async function listMergeScenarios(): Promise<MergeScenarioMeta[]> {
  const response = await fetch(`${BASE}/merge/scenarios`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function compareMergeScenario(name: string): Promise<CompareResult> {
  const response = await fetch(`${BASE}/merge/compare/${name}`, { method: "POST" });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
