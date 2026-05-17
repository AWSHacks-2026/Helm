import type { AppView } from "../components/AppShell";

const VIEWS: AppView[] = [
  "landing",
  "control",
  "incidents",
  "missions",
  "gratitude",
  "proof",
  "labs",
];

export function readInitialView(search = ""): AppView {
  const params = new URLSearchParams(search);
  const view = params.get("view");
  if (view && VIEWS.includes(view as AppView)) {
    return view as AppView;
  }
  return "landing";
}

export function readWalkthroughFlag(search = ""): boolean {
  return new URLSearchParams(search).get("walkthrough") === "1";
}
