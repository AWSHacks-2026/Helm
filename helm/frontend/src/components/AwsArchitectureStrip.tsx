const NODES = [
  { id: "fleet", label: "Agent fleet", detail: "ShopFix + MCP" },
  { id: "helm", label: "Helm API", detail: ":8000" },
  { id: "bedrock", label: "Amazon Bedrock", detail: "Haiku / Sonnet" },
  { id: "memory", label: "AgentCore Memory", detail: "Shared session" },
  { id: "gate", label: "Contention gate", detail: "Rule preflight" },
  { id: "kb", label: "Guardrail KB", detail: "Block before write" },
] as const;

export function AwsArchitectureStrip() {
  return (
    <section className="aws-architecture-strip" aria-label="AWS architecture">
      <p className="eyebrow">Built on AWS</p>
      <div className="aws-architecture-flow">
        {NODES.map((node, index) => (
          <div key={node.id} className="aws-arch-node-wrap">
            {index > 0 && <span className="aws-arch-arrow" aria-hidden="true" />}
            <article className="aws-arch-node">
              <strong>{node.label}</strong>
              <span>{node.detail}</span>
            </article>
          </div>
        ))}
      </div>
    </section>
  );
}
