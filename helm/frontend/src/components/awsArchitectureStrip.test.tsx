import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AwsArchitectureStrip } from "./AwsArchitectureStrip";

describe("AwsArchitectureStrip", () => {
  it("mentions Bedrock and AgentCore", () => {
    const html = renderToStaticMarkup(<AwsArchitectureStrip />);
    expect(html).toContain("Bedrock");
    expect(html).toContain("AgentCore");
  });
});
