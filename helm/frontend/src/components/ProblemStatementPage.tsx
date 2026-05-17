import { PROBLEM_PAGE } from "../content/presentationPages";

export function ProblemStatementPage() {
  return (
    <main className="presentation-page presentation-page--problem">
      <header className="screen-header presentation-hero">
        <div>
          <p className="eyebrow">{PROBLEM_PAGE.eyebrow}</p>
          <h1>{PROBLEM_PAGE.title}</h1>
          <p>{PROBLEM_PAGE.lede}</p>
        </div>
      </header>

      <section className="impact-grid" aria-label="Customer impact">
        {PROBLEM_PAGE.metrics.map((metric) => (
          <article className="metric-card presentation-metric-card" key={metric.label}>
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
            <small>{metric.body}</small>
          </article>
        ))}
      </section>

      <section className="presentation-grid" aria-label="Problem details">
        {PROBLEM_PAGE.sections.map((section) => (
          <article className="presentation-card" key={section.title}>
            <h2>{section.title}</h2>
            <p>{section.body}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
