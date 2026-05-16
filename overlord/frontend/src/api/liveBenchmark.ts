const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type LiveBenchmarkResult = {
  scenario: string;
  mock_bedrock: boolean;
  seed_mode: string;
  comparison: {
    baseline_tokens: number;
    overlord_tokens: number;
    token_savings_pct: number;
    baseline_score: number;
    overlord_score: number;
    overlord_beats_tokens: boolean;
    overlord_beats_quality: boolean;
    baseline_passed: boolean;
    overlord_passed: boolean;
  };
  baseline: { rounds: number; final_code: string };
  overlord: { rounds: number; final_code: string };
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
