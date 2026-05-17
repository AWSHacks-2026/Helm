import type { TraceHelmState } from "../../flightRecorder/types";

type Props = {
  helm: TraceHelmState;
};

const actionLabel: Record<NonNullable<TraceHelmState["action"]>, string> = {
  dedup: "Fleet dedup",
  guardrail: "Guardrail",
  merge: "Merge arbitration",
  gate: "Contention gate",
  reassign: "Reassign agent",
};

export function TraceHelmNode({ helm }: Props) {
  return (
    <article className={`trace-helm-node ${helm.active ? "is-active" : ""}`}>
      <header>
        <h3>Helm</h3>
        <span className="status-chip">{helm.active ? "Active" : "Watching"}</span>
      </header>
      <p>Coordination layer between agents and the repo.</p>
      {helm.active && helm.action && (
        <p className="helm-action">
          {actionLabel[helm.action]}
          {helm.detail ? ` — ${helm.detail}` : ""}
        </p>
      )}
    </article>
  );
}
