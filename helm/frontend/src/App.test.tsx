import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AppView } from "./components/AppShell";
import type { DashboardModel } from "./orchestration/types";

const appHarness = vi.hoisted(() => {
  type LandingPageProps = {
    sessionId: string;
    onSessionIdChange: (sessionId: string) => void;
    onStartReplay: () => void;
    onOpenLiveSession: () => void;
  };

  const model: DashboardModel = {
    mode: "replay",
    title: "Test dashboard",
    subtitle: "Test dashboard subtitle",
    agents: [],
    incidents: [],
    timeline: [],
    metrics: {
      totalAgents: 0,
      activeAgents: 0,
      blockedAgents: 0,
      reassignedAgents: 0,
      completedAgents: 0,
      openIncidents: 0,
      overlordActions: 0,
      tokenSavingsLabel: "0%",
      projectHealth: "clean",
    },
  };

  return {
    landingProps: undefined as LandingPageProps | undefined,
    useDemoReplay: vi.fn(() => ({
      model,
      isPlaying: true,
      isComplete: false,
      play: vi.fn(),
      pause: vi.fn(),
      reset: vi.fn(),
    })),
    useLiveSession: vi.fn(() => ({
      model,
      status: "idle",
      error: null,
      refresh: vi.fn(),
    })),
    reset() {
      this.landingProps = undefined;
      this.useDemoReplay.mockClear();
      this.useLiveSession.mockClear();
    },
  };
});

vi.mock("./hooks/useDemoReplay", () => ({
  useDemoReplay: appHarness.useDemoReplay,
}));

vi.mock("./hooks/useLiveSession", () => ({
  useLiveSession: appHarness.useLiveSession,
}));

vi.mock("./components/AppShell", () => ({
  AppShell: ({
    view,
    children,
  }: {
    view: AppView;
    onViewChange: (view: AppView) => void;
    children: ReactNode;
  }) => (
    <div data-view={view} className="app-shell">
      {children}
    </div>
  ),
}));

vi.mock("./components/LandingPage", () => ({
  LandingPage: (props: {
    sessionId: string;
    onSessionIdChange: (sessionId: string) => void;
    onStartReplay: () => void;
    onOpenLiveSession: () => void;
  }) => {
    appHarness.landingProps = props;

    return <main>Landing page</main>;
  },
}));

vi.mock("./components/ControlTower", () => ({
  ControlTower: () => <main>Control tower</main>,
}));

vi.mock("./components/IncidentConsole", () => ({
  IncidentConsole: () => <main>Incident console</main>,
}));

vi.mock("./components/BenchmarkProof", () => ({
  BenchmarkProof: () => <main>Benchmark proof</main>,
}));

vi.mock("./components/LegacyLabPanel", () => ({
  LegacyLabPanel: () => <main>Developer labs</main>,
}));

describe("App", () => {
  beforeEach(() => {
    appHarness.reset();
    vi.stubGlobal("localStorage", {
      getItem: vi.fn(() => "persisted-session"),
      setItem: vi.fn(),
    });
  });

  it("does not enable replay playback on the landing page", async () => {
    const { default: App } = await import("./App");

    renderToStaticMarkup(<App />);

    expect(appHarness.useDemoReplay).toHaveBeenCalledWith({ enabled: false });
  });

  it("persists session id changes from the landing page", async () => {
    const { default: App } = await import("./App");

    renderToStaticMarkup(<App />);
    appHarness.landingProps?.onSessionIdChange("new-team-session");

    expect(localStorage.setItem).toHaveBeenCalledWith(
      "helm_session_id",
      "new-team-session",
    );
  });
});
