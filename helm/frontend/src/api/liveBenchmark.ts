const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type LiveBenchmarkResult = {
  scenario: string;
  mock_bedrock: boolean;
  seed_mode: string;
  comparison: {
    baseline_tokens: number;
    helm_tokens: number;
    token_savings_pct: number;
    baseline_cost_usd: number;
    helm_cost_usd: number;
    cost_savings_pct: number;
    baseline_cost_display: string;
    helm_cost_display: string;
    helm_beats_cost: boolean;
    cost_note?: string | null;
    baseline_score: number;
    helm_score: number;
    helm_beats_tokens: boolean;
    helm_beats_quality: boolean;
    baseline_passed: boolean;
    helm_passed: boolean;
    baseline_resolution_time_ms?: number;
    helm_resolution_time_ms?: number;
    time_savings_pct?: number;
  };
  baseline: { rounds: number; final_code: string };
  helm: { rounds: number; final_code: string };
};

export async function runLiveBenchmark(
  scenario: string,
  seedMode: "scenario" | "haiku" = "scenario"
): Promise<LiveBenchmarkResult> {
  const response = await fetch(
    `${BASE}/live/benchmark/${scenario}?seed_mode=${seedMode}`,
    { method: "POST" }
  );
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
