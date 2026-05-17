import type { DemoScenario, DemoScenarioId } from "../orchestration/demoScenarios";
import type {
  AgentState,
  DashboardModel,
  IncidentState,
  TimelineEvent,
} from "../orchestration/types";

interface ControlTowerProps {
  model: DashboardModel;
  connectionLabel?: string;
  demoScenarios?: DemoScenario[];
  activeDemoScenarioId?: DemoScenarioId;
  onDemoScenarioChange?: (scenarioId: DemoScenarioId) => void;
  onSelectIncident: (incidentId: string) => void;
}

const titleCase = (value: string): string => {
  const label = value.replace(/_/g, " ");

  return label.charAt(0).toUpperCase() + label.slice(1);
};

const timelineKindLabel: Partial<Record<TimelineEvent["kind"], string>> = {
  intent_declared: "Task registered",
};

const formatTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
      return timestamp;
    }

    return new Intl.DateTimeFormat(undefined, {
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    }).format(date);
  } catch {
    return timestamp;
  }
};

const modeLabel = (_model: DashboardModel): string => "Demo replay";

const projectHealthLabel = (health: DashboardModel["metrics"]["projectHealth"]): string => {
  if (health === "clean") return "Coordinated";
  if (health === "needs_review") return "Needs review";
  return "Blocked";
};

const replayFinished = (connectionLabel?: string): boolean =>
  Boolean(connectionLabel?.toLowerCase().includes("complete"));

const renderAgentCard = (agent: AgentState) => (
  <article key={agent.id} className={`agent-card status-${agent.status}`}>
    <div className="agent-card-header">
      <h3>{agent.name}</h3>
      <span>{titleCase(agent.status)}</span>
    </div>
    <p>{agent.taskTitle}</p>
    {agent.filePath && <code>{agent.filePath}</code>}
  </article>
);

const renderTimelineEvent = (event: TimelineEvent) => (
  <li key={event.id}>
    <time dateTime={event.timestamp}>{formatTimestamp(event.timestamp)}</time>
    <div>
      <strong>{event.title}</strong>
      <p>{event.description}</p>
      <span>{timelineKindLabel[event.kind] ?? titleCase(event.kind)}</span>
    </div>
  </li>
);

const renderIncidentButton = (
  incident: IncidentState,
  onSelectIncident: (incidentId: string) => void,
) => (
  <button
    key={incident.id}
    type="button"
    className={`incident-row status-${incident.status} type-${incident.type}`}
    onClick={() => onSelectIncident(incident.id)}
  >
    <span>{titleCase(incident.type)}</span>
    <strong>{incident.title}</strong>
    <small>{titleCase(incident.status)}</small>
  </button>
);

export function ControlTower({
  model,
  connectionLabel,
  demoScenarios,
  activeDemoScenarioId,
  onDemoScenarioChange,
  onSelectIncident,
}: ControlTowerProps) {
  const { metrics } = model;
  const finished = replayFinished(connectionLabel);
  const showScenarioPicker =
    model.mode === "replay" &&
    demoScenarios &&
    demoScenarios.length > 0 &&
    onDemoScenarioChange;

  return (
    <main className="control-tower">
      {showScenarioPicker && (
        <section className="demo-scenario-picker" aria-label="Demo scenarios">
          <p className="eyebrow">Demo scenarios</p>
          <div className="filter-pills" role="tablist">
            {demoScenarios.map((scenario) => (
              <button
                key={scenario.id}
                type="button"
                role="tab"
                className={activeDemoScenarioId === scenario.id ? "active" : ""}
                onClick={() => onDemoScenarioChange(scenario.id)}
                aria-pressed={activeDemoScenarioId === scenario.id}
              >
                {scenario.label}
              </button>
            ))}
          </div>
        </section>
      )}

      <header className="screen-header">
        <div>
          <p className="eyebrow">{connectionLabel ?? modeLabel(model)}</p>
          <h1>{model.title}</h1>
          <p>
            {finished
              ? (model.completeHint ??
                "Replay finished — open Incidents for detail or Results for charts.")
              : model.subtitle}
          </p>
        </div>
        <span className={`mode-label mode-${model.mode}`}>{modeLabel(model)}</span>
      </header>

      {finished && model.completeHint && (
        <p className="replay-complete-banner" role="status">
          {model.completeHint}
        </p>
      )}

      <section className="metric-grid" aria-label="Dashboard metrics">
        <article className="metric-card">
          <span>Active agents</span>
          <strong>
            {metrics.activeAgents}/{metrics.totalAgents}
          </strong>
          <small>{metrics.blockedAgents} blocked</small>
        </article>
        <article className="metric-card">
          <span>Helm actions</span>
          <strong>{metrics.overlordActions}</strong>
          <small>
            {metrics.openIncidents > 0
              ? `${metrics.openIncidents} open incidents`
              : "No open incidents"}
          </small>
        </article>
        <article className="metric-card">
          <span>Token savings</span>
          <strong>{metrics.tokenSavingsLabel}</strong>
          <small>{metrics.reassignedAgents} reassigned</small>
        </article>
        <article className={`metric-card health-${metrics.projectHealth}`}>
          <span>Project health</span>
          <strong>{projectHealthLabel(metrics.projectHealth)}</strong>
          <small>{metrics.completedAgents} complete</small>
        </article>
      </section>

      <section className="dashboard-grid">
        <section className="dashboard-panel" aria-labelledby="fleet-map-title">
          <h2 id="fleet-map-title">Fleet map</h2>
          {model.agents.length > 0 ? (
            <div className="agent-grid">{model.agents.map(renderAgentCard)}</div>
          ) : (
            <p className="empty-state">No agents are active yet.</p>
          )}
        </section>

        <section className="dashboard-panel" aria-labelledby="timeline-title">
          <h2 id="timeline-title">Decision timeline</h2>
          {model.timeline.length > 0 ? (
            <ol className="timeline-list">{model.timeline.map(renderTimelineEvent)}</ol>
          ) : (
            <p className="empty-state">No timeline events yet.</p>
          )}
        </section>

        <section className="dashboard-panel" aria-labelledby="incidents-title">
          <h2 id="incidents-title">Active and recent incidents</h2>
          {model.incidents.length > 0 ? (
            <div className="incident-row-list">
              {model.incidents.map((incident) =>
                renderIncidentButton(incident, onSelectIncident),
              )}
            </div>
          ) : (
            <p className="empty-state">No incidents detected.</p>
          )}
        </section>
      </section>
    </main>
  );
}
