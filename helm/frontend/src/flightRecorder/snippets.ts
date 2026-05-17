export const SNIPPET_KEYS = [
  "auth_clean",
  "auth_agent_a_edit",
  "auth_agent_b_edit",
  "auth_guardrail_blocked",
  "cart_clean",
  "cart_agent_a_edit",
  "cart_agent_b_edit",
  "cart_conflict",
  "cart_merged",
] as const;

export type SnippetKey = (typeof SNIPPET_KEYS)[number];

const SNIPPETS: Record<SnippetKey, string> = {
  auth_clean: `@router.post("/login")
def login(...):
    token = auth_service.create_access_token(...)`,
  auth_agent_a_edit: `@router.post("/login")
def login(...):
    # agent_a: shorter TTL window
    token = auth_service.create_access_token(..., ttl=900)`,
  auth_agent_b_edit: `@router.post("/login")
def login(...):
    # agent_b: OAuth callback validation
    auth_service.validate_oauth_callback(...)`,
  auth_guardrail_blocked: `# BLOCKED: delete session store
# reverses_recent_decision`,
  cart_clean: `def checkout_total(cart, customer):
    return sum(line.price for line in cart.lines)`,
  cart_agent_a_edit: `def checkout_total(cart, customer):
    return apply_subscription_proration(...)`,
  cart_agent_b_edit: `def checkout_total(cart, customer):
    tax = tax_service.compute(...)
    return subtotal + tax`,
  cart_conflict: `<<<<<<< agent/agent_a
apply_subscription_proration(...)
=======
 tax_service.compute(...)
>>>>>>> agent/agent_b`,
  cart_merged: `def checkout_total(cart, customer):
    tax = tax_service.compute(...)
    return apply_subscription_proration(subtotal + tax, ...)`,
};

export function getSnippet(key: SnippetKey): string {
  return SNIPPETS[key];
}
