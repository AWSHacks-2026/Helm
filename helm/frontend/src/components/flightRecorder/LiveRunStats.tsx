import type { FlightTraceMeta } from "../../flightRecorder/types";

interface LiveRunStatsProps {
  meta: FlightTraceMeta | undefined;
}

export function LiveRunStats({ meta }: LiveRunStatsProps) {
  if (!meta?.source_matrix) {
    return null;
  }

  const path = meta.path_mode ?? "helm";
  const savings =
    meta.cost_savings_pct != null && path === "helm"
      ? `${meta.cost_savings_pct}% cost · ${meta.token_savings_pct ?? "—"}% tokens · ${meta.time_savings_pct ?? "—"}% time vs baseline`
      : null;

  return (
    <aside className="live-run-stats" aria-label="Live run metrics">
      <p>
        <strong>Source:</strong> {basename(meta.source_matrix)}
        {meta.generated_at ? ` · ${meta.generated_at.slice(0, 19)}Z` : ""}
      </p>
      {path === "helm" && meta.baseline_cost && meta.helm_cost && (
        <p>
          <strong>Measured:</strong> {meta.baseline_cost} baseline → {meta.helm_cost} helm
          {savings ? ` (${savings})` : ""}
        </p>
      )}
      {path === "helm" && (
        <p className="live-run-stats-detail">
          Gate {meta.gate_skipped || meta.helm_gate_skipped ? "skipped" : "ran"}
          {meta.guardrails_blocked != null
            ? ` · ${meta.guardrails_blocked} guardrail blocks`
            : ""}
          {meta.dedup_calls != null || meta.helm_dedup_calls != null
            ? ` · dedup ${meta.dedup_calls ?? meta.helm_dedup_calls ?? 0}`
            : ""}
        </p>
      )}
      {path === "baseline" && meta.baseline_tokens != null && (
        <p className="live-run-stats-detail">
          {meta.baseline_tokens.toLocaleString()} tokens · no Helm coordination
        </p>
      )}
    </aside>
  );
}

function basename(path: string): string {
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] ?? path;
}
