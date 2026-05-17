import { SOLUTION_PAGE } from "../content/presentationPages";

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

      <section className="coordination-diagram" aria-label="Overlord coordination flow">
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
    </main>
  );
}
