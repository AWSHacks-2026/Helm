import DemoLab from "../DemoLab";
import MergeLab from "../MergeLab";

export function LegacyLabPanel() {
  return (
    <main className="legacy-lab-panel">
      <header className="screen-header">
        <div>
          <p className="eyebrow">Existing demo tools</p>
          <h1>Developer Labs</h1>
          <p>
            Keep the original merge and demo labs available for lower-level
            scenario testing.
          </p>
        </div>
      </header>

      <section className="legacy-grid" aria-label="Existing demo tools">
        <MergeLab />
        <DemoLab />
      </section>
    </main>
  );
}
