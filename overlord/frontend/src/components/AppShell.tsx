import type { ReactNode } from "react";

export type AppView = "landing" | "control" | "incidents" | "proof" | "labs";

interface AppShellProps {
  view: AppView;
  onViewChange: (view: AppView) => void;
  children: ReactNode;
}

const navItems: Array<{ view: AppView; label: string }> = [
  { view: "control", label: "Control Tower" },
  { view: "incidents", label: "Incidents" },
  { view: "proof", label: "Benchmark Proof" },
  { view: "labs", label: "Developer Labs" },
];

export function AppShell({ view, onViewChange, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <nav className="app-nav" aria-label="Primary navigation">
        <button
          type="button"
          className={`brand-button ${view === "landing" ? "active" : ""}`}
          onClick={() => onViewChange("landing")}
        >
          Overlord
        </button>
        {navItems.map((item) => (
          <button
            key={item.view}
            type="button"
            className={view === item.view ? "active" : ""}
            onClick={() => onViewChange(item.view)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <div className="app-shell-content">{children}</div>
    </div>
  );
}
