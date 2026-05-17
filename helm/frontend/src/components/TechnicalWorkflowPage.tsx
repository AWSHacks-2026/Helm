import { TECHNICAL_WORKFLOW_PAGE } from "../content/presentationPages";

export function TechnicalWorkflowPage() {
  return (
    <main className="presentation-page presentation-page--technical">
      <header className="screen-header presentation-hero">
        <div>
          <p className="eyebrow">{TECHNICAL_WORKFLOW_PAGE.eyebrow}</p>
          <h1>{TECHNICAL_WORKFLOW_PAGE.title}</h1>
          <p>{TECHNICAL_WORKFLOW_PAGE.lede}</p>
        </div>
        <div className="technical-badge-stack" aria-label="AWS services used">
          {TECHNICAL_WORKFLOW_PAGE.badges.map((badge) => (
            <span key={badge}>{badge}</span>
          ))}
        </div>
      </header>

      <section className="architecture-panel" aria-labelledby="technical-architecture-title">
        <div className="architecture-panel-header">
          <div>
            <p className="eyebrow">Source-backed flowchart</p>
            <h2 id="technical-architecture-title">Helm / MergeAI system architecture</h2>
          </div>
          <p>Adapted from <code>helm_architecture.html</code>.</p>
        </div>

        <div className="architecture-flowchart">
          {TECHNICAL_WORKFLOW_PAGE.lanes.map((lane) => (
            <section className="architecture-lane" key={lane.label}>
              <div className="architecture-lane-label">{lane.label}</div>
              <div className="architecture-lane-body">
                <div className="architecture-node-row">
                  {lane.nodes.map((node) => (
                    <div className="architecture-node-wrap" key={`${lane.label}-${node.title}`}>
                      <article className={`architecture-node architecture-node--${node.tone}`}>
                        <strong>{node.title}</strong>
                        <span>{node.detail}</span>
                      </article>
                    </div>
                  ))}
                </div>
                {lane.note && <p className="architecture-lane-note">{lane.note}</p>}
              </div>
            </section>
          ))}
        </div>
      </section>

      <section className="impact-grid" aria-label="Technical stack">
        {TECHNICAL_WORKFLOW_PAGE.metrics.map((metric) => (
          <article className="metric-card presentation-metric-card" key={metric.label}>
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
            <small>{metric.body}</small>
          </article>
        ))}
      </section>

      <section className="presentation-grid" aria-label="AWS and Bedrock details">
        {TECHNICAL_WORKFLOW_PAGE.sections.map((section) => (
          <article className="presentation-card" key={section.title}>
            <h2>{section.title}</h2>
            <p>{section.body}</p>
          </article>
        ))}
      </section>

      <section className="env-switch-panel" aria-label="Demo environment switches">
        <p className="eyebrow">Runtime switches</p>
        <dl>
          {TECHNICAL_WORKFLOW_PAGE.envSwitches.map((item) => (
            <div key={item.name}>
              <dt>{item.name}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </main>
  );
}
