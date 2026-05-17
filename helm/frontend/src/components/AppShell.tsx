import type { ReactNode } from "react";

import { HELM_MARK_ARIA, HELM_TAGLINE } from "../content/gratitudeMission";
import { readPresenterMode } from "../hooks/usePresenterMode";
import { HelmMark } from "./HelmMark";

export type AppView =
  | "landing"
  | "problem"
  | "solution"
  | "technical"
  | "control"
  | "recorder"
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
  { view: "problem", label: "Problem Statement" },
  { view: "solution", label: "Our Solution" },
  { view: "technical", label: "Technical Workflow" },
  { view: "control", label: "Control Tower" },
  { view: "recorder", label: "Under the hood" },
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
          aria-label={HELM_MARK_ARIA}
          onClick={() => onViewChange("landing")}
        >
          <span className="brand-lockup">
            <HelmMark size={22} />
            <span className="brand-text">
              <span className="brand-name">Helm</span>
              <span className="brand-tagline">{HELM_TAGLINE}</span>
            </span>
          </span>
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
