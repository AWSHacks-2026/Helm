import { useEffect, useState } from "react";

import { fetchDemoManifest, type DemoBenchmarkManifest } from "../api/demoManifest";
import { DEMO_PILLARS, type DemoPillar, type DemoPillarId } from "../demoHeadlines";
import { readPresenterMode } from "../hooks/usePresenterMode";

function applyManifest(pillars: DemoPillar[], manifest: DemoBenchmarkManifest): DemoPillar[] {
  return pillars.map((pillar) => {
    const live = manifest.pillars[pillar.id as DemoPillarId];
    if (!live) return pillar;
    return {
      ...pillar,
      headline: live.headline ?? pillar.headline,
      costSavingsPct: live.cost_savings_pct ?? pillar.costSavingsPct,
      wallSavingsPct: live.wall_savings_pct ?? pillar.wallSavingsPct,
    };
  });
}

export function PillarHeadlineCards() {
  const [pillars, setPillars] = useState(DEMO_PILLARS);
  const [manifestSource, setManifestSource] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const presenterMode =
    typeof window !== "undefined" && readPresenterMode(window.location.search);

  useEffect(() => {
    let cancelled = false;
    fetchDemoManifest()
      .then((manifest) => {
        if (cancelled) return;
        setPillars(applyManifest(DEMO_PILLARS, manifest));
        setManifestSource(manifest.matrix_source);
      })
      .catch(() => {
        /* static DEMO_PILLARS fallback */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleRefresh() {
    setRefreshError(null);
    try {
      const manifest = await fetchDemoManifest();
      setPillars(applyManifest(DEMO_PILLARS, manifest));
      setManifestSource(manifest.matrix_source);
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="pillar-headline-grid" role="region" aria-label="Benchmark headlines">
      {!presenterMode && (
        <div className="pillar-headline-toolbar">
          <button type="button" onClick={handleRefresh}>
            Refresh from latest matrix
          </button>
          {manifestSource && (
            <span className="demo-hint">Source: {manifestSource}</span>
          )}
          {refreshError && <span className="demo-error">{refreshError}</span>}
        </div>
      )}
      {pillars.map((pillar) => (
        <div key={pillar.id} className={`pillar-card pillar-${pillar.id}`}>
          <p className="eyebrow">{pillar.label}</p>
          <h2>{pillar.headline}</h2>
          <p>{pillar.subline}</p>
          {(pillar.costSavingsPct != null || pillar.wallSavingsPct != null) && (
            <dl className="pillar-metrics">
              {pillar.costSavingsPct != null && (
                <div>
                  <dt>Cost</dt>
                  <dd>+{pillar.costSavingsPct}%</dd>
                </div>
              )}
              {pillar.wallSavingsPct != null && (
                <div>
                  <dt>Wall</dt>
                  <dd>+{pillar.wallSavingsPct}%</dd>
                </div>
              )}
            </dl>
          )}
          <div className="pillar-card-footer">
            <span className="aws-tags">{pillar.awsServices.join(" · ")}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
