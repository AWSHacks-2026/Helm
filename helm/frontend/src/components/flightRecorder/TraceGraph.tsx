import type { TraceEdge, TraceFrame } from "../../flightRecorder/types";
import { TraceAgentNode } from "./TraceAgentNode";
import { TraceHelmNode } from "./TraceHelmNode";

type Props = {
  frame: TraceFrame;
};

const WIDTH = 820;
const HEIGHT = 400;

const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  agent_a: { x: 140, y: 100 },
  agent_b: { x: 680, y: 100 },
  helm: { x: 410, y: 320 },
};

const edgeStroke: Record<TraceEdge["kind"], string> = {
  idle: "var(--edge-idle)",
  coding: "var(--edge-coding)",
  blocked: "var(--edge-blocked)",
  reassigned: "var(--edge-reassigned)",
  conflicted: "var(--edge-conflicted)",
  complete: "var(--edge-complete)",
  dedup: "var(--edge-dedup)",
  guardrail: "var(--edge-guardrail)",
  merge: "var(--edge-merge)",
};

function helmToAgentPath(
  from: { x: number; y: number },
  to: { x: number; y: number },
): string {
  const cx = (from.x + to.x) / 2;
  const cy = from.y + (to.y - from.y) * 0.42;
  return `M ${from.x} ${from.y} Q ${cx} ${cy} ${to.x} ${to.y}`;
}

function renderEdge(edge: TraceEdge) {
  const from = NODE_POSITIONS.helm;
  const to = NODE_POSITIONS[edge.to] ?? NODE_POSITIONS.agent_a;
  const active = edge.kind !== "idle";
  return (
    <g key={`${edge.to}-${edge.kind}`} className={`trace-edge trace-edge-${edge.kind}`}>
      <path
        d={helmToAgentPath(from, to)}
        fill="none"
        stroke={edgeStroke[edge.kind]}
        strokeWidth={active ? 3 : 1.5}
        strokeDasharray={active ? undefined : "6 6"}
        opacity={active ? 1 : 0.55}
        markerEnd={active ? "url(#trace-arrow)" : undefined}
      />
      {active && (
        <text
          x={(from.x + to.x) / 2}
          y={(from.y + to.y) / 2 - 10}
          className="trace-edge-label"
          textAnchor="middle"
        >
          {edge.kind}
        </text>
      )}
    </g>
  );
}

export function TraceGraph({ frame }: Props) {
  const [left, right] = frame.agents;

  return (
    <section className="trace-graph" aria-label="Agent and Helm coordination graph">
      <svg
        className="trace-graph-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Helm connected to subagents"
      >
        <defs>
          <marker
            id="trace-arrow"
            markerWidth="8"
            markerHeight="8"
            refX="6"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6 Z" fill="context-stroke" />
          </marker>
        </defs>
        {frame.edges.map((edge) => renderEdge(edge))}
      </svg>
      <div className="trace-graph-nodes">
        {left && (
          <div className="trace-graph-node trace-graph-node-a">
            <TraceAgentNode agent={left} />
          </div>
        )}
        {right && (
          <div className="trace-graph-node trace-graph-node-b">
            <TraceAgentNode agent={right} />
          </div>
        )}
        <div className="trace-graph-node trace-graph-node-helm">
          <TraceHelmNode helm={frame.helm} />
        </div>
      </div>
    </section>
  );
}
