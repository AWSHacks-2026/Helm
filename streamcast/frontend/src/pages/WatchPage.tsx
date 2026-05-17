import React from "react";

type Props = { streamTitle?: string };

export function WatchPage({ streamTitle = "Live stream" }: Props) {
  const accent =
    typeof document !== "undefined"
      ? getComputedStyle(document.documentElement).getPropertyValue("--agent-accent").trim() ||
        "#9147ff"
      : "#9147ff";

  return (
    <main style={{ fontFamily: "system-ui", padding: 24, borderTop: `4px solid ${accent}` }}>
      <h1 style={{ color: accent }}>{streamTitle}</h1>
      <div
        style={{
          background: "#111",
          color: "#fff",
          aspectRatio: "16/9",
          display: "grid",
          placeItems: "center",
          borderRadius: 8,
        }}
      >
        Player placeholder
      </div>
      <p style={{ marginTop: 12 }}>Per-agent theme via --agent-accent</p>
    </main>
  );
}
