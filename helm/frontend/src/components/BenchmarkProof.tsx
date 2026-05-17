import { DemoChartGallery } from "./DemoChartGallery";
import { LiveGuardrailDemo } from "./LiveGuardrailDemo";
import { PillarHeadlineCards } from "./PillarHeadlineCards";
import { HACKATHON_THEME, PRODUCT_NAME, RESULTS_INTRO } from "../content/gratitudeMission";
import { readPresenterMode } from "../hooks/usePresenterMode";

export function BenchmarkProof() {
  const presenterMode =
    typeof window !== "undefined" && readPresenterMode(window.location.search);

  return (
    <main className={`benchmark-proof ${presenterMode ? "benchmark-proof--presenter" : ""}`}>
      <header className="screen-header">
        <div>
          <p className="eyebrow">
            {HACKATHON_THEME} · {PRODUCT_NAME} · ShopFix · Amazon Bedrock
          </p>
          <h1>{presenterMode ? "Proof we gave time back" : "Benchmark results"}</h1>
          <p>{RESULTS_INTRO}</p>
        </div>
      </header>

      <PillarHeadlineCards />

      <DemoChartGallery />

      <LiveGuardrailDemo />
    </main>
  );
}
