import type { ReactNode } from "react";

import { readPresenterMode } from "../hooks/usePresenterMode";

export type AppView =
  | "landing"
  | "control"
  | "incidents"
  | "missions"
  | "gratitude"
  | "proof"
  | "labs";

interface AppShellProps {
  view: AppView;
  onViewChange: (view: AppView) => void;
  children: ReactNode;
}

const navItems: Array<{ view: AppView; label: string }> = [
  { view: "control", label: "Control Tower" },
  { view: "incidents", label: "Incidents" },
  { view: "gratitude", label: "Gratitude" },
  { view: "proof", label: "Results" },
  { view: "labs", label: "Developer Labs" },
];

export function AppShell({ view, onViewChange, children }: AppShellProps) {
  const presenterMode =
    typeof window !== "undefined" && readPresenterMode(window.location.search);
  const navItemsFiltered = presenterMode
    ? navItems.filter((item) => item.view !== "labs")
    : navItems;

  return (
    <div className="app-shell">
      <nav className="app-nav" aria-label="Primary navigation">
        <button
          type="button"
          className={`brand-button ${view === "landing" ? "active" : ""}`}
          onClick={() => onViewChange("landing")}
        >
          Helm
        </button>
        {navItemsFiltered.map((item) => (
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
