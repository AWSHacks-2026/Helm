const ACTS = [
  {
    title: "Act 1: Gate (disjoint)",
    script:
      "Six agents, six files, zero overlap. Helm runs the contention gate with zero dedup Bedrock calls. Same cost as baseline. Pytest still passes.",
  },
  {
    title: "Act 2: Duplicate work (contention N=8)",
    script:
      "Baseline runs eight agents on overlapping files. Helm dedupes first. Six agents run. About eighteen percent cheaper and thirty-nine percent faster wall clock.",
  },
  {
    title: "Act 3: Merge fleet",
    script:
      "When git actually conflicts on two files, parallel per-file Haiku merge-fix cuts merge-phase wall time about thirty percent at N equals six.",
  },
  {
    title: "Act 4: Guardrails (ShopFix auth)",
    script:
      "On ShopFix auth.py the guardrail blocks a destructive delete before write. About forty-five percent cost and fifty-five percent wall versus running the bad edit twice.",
  },
];

export function PresenterScript() {
  return (
    <details className="presenter-script" open>
      <summary>Presenter script (60s)</summary>
      <ol>
        {ACTS.map((act) => (
          <li key={act.title}>
            <strong>{act.title}</strong>
            <p>{act.script}</p>
          </li>
        ))}
      </ol>
      <div className="presenter-script-footer">
        <p>
          Presenter mode: add <code>?presenter=1</code> or <code>?demo=1</code> to the URL
          (for example <code>http://localhost:5173/?presenter=1</code>).
        </p>
      </div>
    </details>
  );
}
