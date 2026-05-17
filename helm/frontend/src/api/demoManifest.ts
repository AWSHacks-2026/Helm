const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export type ManifestPillar = {
  cost_savings_pct?: number;
  wall_savings_pct?: number;
  headline?: string;
};

export type DemoBenchmarkManifest = {
  generated_at: string;
  matrix_source: string;
  pillars: {
    gate: ManifestPillar;
    contention: ManifestPillar;
    merge: ManifestPillar;
    guardrails: ManifestPillar;
  };
};

export async function fetchDemoManifest(): Promise<DemoBenchmarkManifest> {
  const response = await fetch(`${BASE}/demo/benchmark-manifest`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
