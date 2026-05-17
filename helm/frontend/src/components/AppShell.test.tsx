import { Children, isValidElement, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

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
  it("renders top navigation, active state, and page content", () => {
    const html = renderToStaticMarkup(
      <AppShell view="proof" onViewChange={() => undefined}>
        <section>Selected page</section>
      </AppShell>,
    );

    expect(html).toContain("Helm");
    expect(html).toContain("Control Tower");
    expect(html).toContain("Incidents");
    expect(html).not.toContain("Missions");
    expect(html).toContain("Gratitude");
    expect(html).toContain("Results");
    expect(html).toContain("Developer Labs");
    expect(html).toContain("app-shell");
    expect(html).toContain("Selected page");
    expect(html).toContain("class=\"active\"");
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

    (buttonsByLabel.get("Helm")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Control Tower")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Incidents")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Gratitude")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Results")?.props as ButtonProps).onClick?.();
    (buttonsByLabel.get("Developer Labs")?.props as ButtonProps).onClick?.();

    expect(onViewChange).toHaveBeenNthCalledWith(1, "landing" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(2, "control" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(3, "incidents" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(4, "gratitude" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(5, "proof" satisfies AppView);
    expect(onViewChange).toHaveBeenNthCalledWith(6, "labs" satisfies AppView);
    expect((buttonsByLabel.get("Control Tower")?.props as ButtonProps).className).toBe(
      "active",
    );
  });
});
