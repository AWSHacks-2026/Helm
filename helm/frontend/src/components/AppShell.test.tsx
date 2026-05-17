import { Children, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell, type AppView } from "./AppShell";

type PropsWithChildren = {
  children?: ReactNode;
};

type ButtonProps = {
  onClick?: () => void;
  className?: string;
};

const walkElements = (node: ReactNode): ReactElement[] => {
  const elements: ReactElement[] = [];

  Children.forEach(node, (child) => {
    if (!isValidElement(child)) {
      return;
    }

    elements.push(child);
    elements.push(...walkElements((child.props as PropsWithChildren).children));
  });

  return elements;
};

const textContent = (node: ReactNode): string => {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }

  if (!isValidElement(node)) {
    return "";
  }

  return Children.toArray((node.props as PropsWithChildren).children)
    .map(textContent)
    .join("");
};

describe("AppShell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders top navigation, active state, and page content", () => {
    const html = renderToStaticMarkup(
      <AppShell view="proof" onViewChange={() => undefined}>
        <section>Selected page</section>
      </AppShell>,
    );

    expect(html).toContain("helm-mark");
    expect(html).toContain("Steer the agent fleet");
    expect(html).toContain("Problem Statement");
    expect(html).toContain("Our Solution");
    expect(html).toContain("Technical Workflow");
    expect(html).toContain("Control Tower");
    expect(html).toContain("Under the hood");
    expect(html).toContain("Incidents");
    expect(html).not.toContain("Missions");
    expect(html).toContain("Gratitude");
    expect(html).toContain("Results");
    expect(html).toContain("Developer Labs");
    expect(html).toContain("app-shell");
    expect(html).toContain("Selected page");
    expect(html).toContain("class=\"active\"");
  });

  it("keeps Results visible in presenter mode while hiding Developer Labs", () => {
    vi.stubGlobal("window", { location: { search: "?presenter=1" } });

    const html = renderToStaticMarkup(
      <AppShell view="proof" onViewChange={() => undefined}>
        <section>Selected page</section>
      </AppShell>,
    );

    expect(html).toContain("Problem Statement");
    expect(html).toContain("Our Solution");
    expect(html).toContain("Technical Workflow");
    expect(html).toContain("Control Tower");
    expect(html).toContain("Incidents");
    expect(html).toContain("Gratitude");
    expect(html).toContain("Results");
    expect(html).not.toContain("Developer Labs");
  });

  it("wires nav buttons to view changes", () => {
    const onViewChange = vi.fn();
    const root = AppShell({
      view: "control",
      onViewChange,
      children: <section>Selected page</section>,
    });
    const buttons = walkElements(root).filter((element) => element.type === "button");
    const buttonsByLabel = new Map(
      buttons.map((button) => [textContent(button), button]),
    );

    const brandButton = buttons.find((button) =>
      ((button.props as ButtonProps).className ?? "").includes("brand-button"),
    );
    (brandButton?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Problem Statement")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Our Solution")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Technical Workflow")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Control Tower")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Under the hood")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Incidents")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Gratitude")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Results")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Developer Labs")?.props as ButtonProps).onClick?.();

    expect(onViewChange).toHaveBeenNthCalledWith(1, "landing" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(2, "problem" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(3, "solution" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(4, "technical" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(5, "control" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(6, "recorder" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(7, "incidents" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(8, "gratitude" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(9, "proof" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(10, "labs" satisfies AppView);
    expect((buttonsByLabel.get("Control Tower")?.props as ButtonProps).className).toBe(
      "active",
    );
  });
});
