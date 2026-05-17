import { formatAgentName } from "../../content/agentPersonas";
import type { TraceAgentState } from "../../flightRecorder/types";

type Props = {
  agent: TraceAgentState;
};

const titleCase = (value: string): string =>
  value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, " ");

export function TraceAgentNode({ agent }: Props) {
  return (
    <article className={`trace-agent-node status-${agent.status}`}>
      <header>
        <h3>{formatAgentName(agent.id)}</h3>
        <span className="status-chip">{titleCase(agent.status)}</span>
      </header>
      <p>{agent.taskTitle}</p>
      <code>{agent.filePath}</code>
    </article>
  );
}
