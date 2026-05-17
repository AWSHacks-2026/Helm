import { useCallback, useEffect, useState } from "react";

import {
  ALL_DEMO_CHARTS,
  FEATURED_DEMO_CHART,
  PILLAR_DEMO_CHARTS,
  type DemoChart,
} from "../demoCharts";
import { readPresenterMode } from "../hooks/usePresenterMode";

const pillarLabel: Record<DemoChart["pillar"], string> = {
  overview: "Overview",
  contention: "Contention",
  merge: "Merge",
  guardrails: "Guardrails",
};

function ChartFigure({
  chart,
  onExpand,
  layout = "card",
}: {
  chart: DemoChart;
  onExpand: (chart: DemoChart) => void;
  layout?: "hero" | "card";
}) {
  return (
    <figure className={`demo-chart-figure layout-${layout}`}>
      <button
        type="button"
        className="demo-chart-button"
        onClick={() => onExpand(chart)}
        aria-label={`Expand ${chart.title}`}
      >
        <img src={chart.src} alt={chart.title} loading="lazy" decoding="async" />
      </button>
      <figcaption>
        <span className={`demo-chart-pillar pillar-${chart.pillar}`}>
          {pillarLabel[chart.pillar]}
        </span>
        <h3>{chart.title}</h3>
        <p>{chart.caption}</p>
      </figcaption>
    </figure>
  );
}

export function DemoChartGallery() {
  const presenterMode =
    typeof window !== "undefined" && readPresenterMode(window.location.search);
  const [expanded, setExpanded] = useState<DemoChart | null>(null);
  const [slideshow, setSlideshow] = useState(presenterMode);
  const [slideIndex, setSlideIndex] = useState(0);

  const closeLightbox = useCallback(() => {
    setExpanded(null);
  }, []);

  useEffect(() => {
    if (!expanded) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeLightbox();
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [closeLightbox, expanded]);

  useEffect(() => {
    if (!slideshow) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "ArrowRight") {
        setSlideIndex((index) => Math.min(index + 1, ALL_DEMO_CHARTS.length - 1));
      }
      if (event.key === "ArrowLeft") {
        setSlideIndex((index) => Math.max(index - 1, 0));
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [slideshow]);

  const slideChart = ALL_DEMO_CHARTS[slideIndex] ?? FEATURED_DEMO_CHART;

  return (
    <section className="demo-chart-gallery" aria-label="ShopFix benchmark charts">
      <header className="demo-chart-gallery-header">
        <div>
          <p className="eyebrow">Measured on ShopFix</p>
          <h2>{presenterMode ? "Benchmark charts" : "Charts"}</h2>
          <p>
            {presenterMode
              ? "Click any chart to enlarge · ← → to move through the deck."
              : "Live AWS benchmark plots — click to enlarge."}
          </p>
        </div>
        {presenterMode && slideshow && (
          <span className="slideshow-indicator">
            {slideIndex + 1} / {ALL_DEMO_CHARTS.length}
          </span>
        )}
        {!presenterMode && (
          <div className="demo-chart-slideshow-controls">
            <button
              type="button"
              className={slideshow ? "active" : ""}
              onClick={() => setSlideshow((value) => !value)}
            >
              {slideshow ? "Grid view" : "Slideshow"}
            </button>
          </div>
        )}
      </header>

      {slideshow ? (
        <ChartFigure chart={slideChart} onExpand={setExpanded} layout="hero" />
      ) : (
        <>
          <ChartFigure
            chart={FEATURED_DEMO_CHART}
            onExpand={setExpanded}
            layout="hero"
          />
          <div className="demo-chart-grid">
            {PILLAR_DEMO_CHARTS.map((chart) => (
              <ChartFigure key={chart.id} chart={chart} onExpand={setExpanded} />
            ))}
          </div>
        </>
      )}

      {expanded && (
        <div
          className="demo-chart-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label={expanded.title}
          onClick={closeLightbox}
        >
          <div
            className="demo-chart-lightbox-panel"
            onClick={(event) => event.stopPropagation()}
          >
            <button type="button" className="demo-chart-close" onClick={closeLightbox}>
              Close
            </button>
            <img src={expanded.src} alt={expanded.title} />
            <p>{expanded.caption}</p>
          </div>
        </div>
      )}
    </section>
  );
}
