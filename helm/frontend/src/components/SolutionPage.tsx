import { SOLUTION_PAGE } from "../content/presentationPages";
import agentsRuntimeChart from "../../../../Agents vs Runtime (seconds).png";
import agentsTokensChart from "../../../../Agents vs Tokens Consumed.png";

export function SolutionPage() {
  return (
    <main className="presentation-page presentation-page--solution">
      <header className="screen-header presentation-hero">
        <div>
          <p className="eyebrow">{SOLUTION_PAGE.eyebrow}</p>
          <h1>{SOLUTION_PAGE.title}</h1>
          <p>{SOLUTION_PAGE.lede}</p>
        </div>
      </header>

      <section className="coordination-diagram" aria-label="Helm coordination flow">
        <span>Agents</span>
        <span className="coordination-arrow">Intent</span>
        <span>Helm</span>
        <span className="coordination-arrow">Coordinate</span>
        <span>Safe parallel work</span>
      </section>

      <section className="impact-grid" aria-label="Solution steps">
        {SOLUTION_PAGE.metrics.map((metric) => (
          <article className="metric-card presentation-metric-card" key={metric.label}>
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
            <small>{metric.body}</small>
          </article>
        ))}
      </section>

      <section className="presentation-grid" aria-label="Solution details">
        {SOLUTION_PAGE.sections.map((section) => (
          <article className="presentation-card" key={section.title}>
            <h2>{section.title}</h2>
            <p>{section.body}</p>
          </article>
        ))}
      </section>

      <section className="solution-research-panel" aria-labelledby="solution-research-title">
        <div className="solution-research-copy">
          <p className="eyebrow">Research model</p>
          <h2 id="solution-research-title">Research model: worst-case thrash vs Helm</h2>
          <p>
            These charts show the theoretical shape of the problem Helm is built to
            prevent. The worst-case line is when every agent conflicts with every
            other agent and each one tries to resolve those collisions on its own.
            Every added agent creates N more conflicts, so token use and runtime
            trend toward exponential growth.
          </p>
          <p>
            Helm changes the curve by moving conflict handling into one coordinator.
            Agents still scale with the size of the fleet, but coordination becomes
            centralized: detect overlap once, dedupe work once, arbitrate hard merges
            once. That turns the conflict path from runaway thrash into linear growth
            with the number of agents.
          </p>
        </div>

        <div className="solution-research-charts">
          <figure>
            <img src={agentsTokensChart} alt="Agents vs Tokens Consumed" />
            <figcaption>Agents vs Tokens Consumed</figcaption>
          </figure>
          <figure>
            <img src={agentsRuntimeChart} alt="Agents vs Runtime" />
            <figcaption>Agents vs Runtime</figcaption>
          </figure>
        </div>
      </section>
    </main>
  );
}
