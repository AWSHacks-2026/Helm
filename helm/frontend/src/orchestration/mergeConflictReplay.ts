import { demoAgent, demoIncident } from "./demoScenarioHelpers";
import type { TimelineEvent } from "./types";

const T0 = "2026-05-17T16:10:00.000Z";
const CART_PATH = "backend/app/routers/cart.py";

/** ShopFix merge conflict — two agents collide on cart checkout, Helm resolves with Sonnet. */
export const createMergeConflictReplayEvents = (): TimelineEvent[] => {
  const mergeIncident = demoIncident(
    "incident-cart-merge",
    "merge_conflict",
    "open",
    "Merge conflict on ShopFix cart.py",
    "agent_a added subscription proration hooks while agent_b rewrote checkout tax lines on the same router.",
    ["agent_a", "agent_b"],
    "2026-05-17T16:12:30.000Z",
    {
      filePath: CART_PATH,
      reasoning:
        "Both branches touched checkout_total() — caching decorator vs tax-inclusive pricing.",
      suggestedTask: "Continue catalog facets work on disjoint file",
    },
  );

  const resolvedIncident = demoIncident(
    mergeIncident.id,
    "merge_conflict",
    "resolved",
    mergeIncident.title,
    "Helm combined proration hooks with tax-inclusive checkout_total().",
    mergeIncident.agentIds,
    "2026-05-17T16:13:45.000Z",
    {
      filePath: CART_PATH,
      reasoning:
        "Sonnet arbitration preserved subscription proration and region-aware tax in one checkout_total().",
      resolvedCode: `def checkout_total(cart: Cart, customer: Customer) -> Money:
    subtotal = sum(line.price for line in cart.lines)
    tax = tax_service.compute(subtotal, customer.region)
    return apply_subscription_proration(subtotal + tax, customer.plan)`,
    },
  );

  return [
    {
      id: "merge-001",
      timestamp: T0,
      kind: "agent_started",
      title: "agent_a started on cart.py",
      description: "Subscription proration hooks on ShopFix cart router.",
      agent: demoAgent("agent_a", "agent_a", "Cart proration hooks", CART_PATH),
    },
    {
      id: "merge-002",
      timestamp: "2026-05-17T16:10:12.000Z",
      kind: "agent_started",
      title: "agent_b started on cart.py",
      description: "Tax-inclusive checkout totals on the same file.",
      agent: demoAgent("agent_b", "agent_b", "Tax-inclusive checkout", CART_PATH),
    },
    {
      id: "merge-003",
      timestamp: "2026-05-17T16:11:00.000Z",
      kind: "intent_declared",
      title: "agent_a registered task on cart.py",
      description: "Proration changes tracked before edit.",
      agentId: "agent_a",
      taskTitle: "Cart proration hooks",
      filePath: CART_PATH,
    },
    {
      id: "merge-004",
      timestamp: "2026-05-17T16:11:30.000Z",
      kind: "intent_declared",
      title: "agent_b registered task on cart.py",
      description: "Overlapping checkout_total() edits detected.",
      agentId: "agent_b",
      taskTitle: "Tax-inclusive checkout",
      filePath: CART_PATH,
    },
    {
      id: "merge-005",
      timestamp: "2026-05-17T16:12:30.000Z",
      kind: "merge_detected",
      title: "Merge conflict on cart.py",
      description: "Git conflict markers in checkout_total — queued for Helm arbitration.",
      agentId: "agent_b",
      incident: mergeIncident,
    },
    {
      id: "merge-006",
      timestamp: "2026-05-17T16:13:45.000Z",
      kind: "merge_resolved",
      title: "Helm merged cart.py with Sonnet",
      description:
        "Unified proration + tax lines — ~2,400 tokens saved vs two agents fixing independently.",
      agentId: "agent_a",
      incidentId: mergeIncident.id,
      incident: resolvedIncident,
    },
    {
      id: "merge-007",
      timestamp: "2026-05-17T16:14:00.000Z",
      kind: "benchmark_result",
      title: "Merge fleet benchmark",
      description: "ShopFix merge scenario: Helm score 94% vs best naive 71%.",
      benchmark: {
        tokenSavingsLabel: "39%",
        baselineTokens: 4800,
        overlordTokens: 2928,
      },
    },
    {
      id: "merge-008",
      timestamp: "2026-05-17T16:14:15.000Z",
      kind: "intent_declared",
      title: "Cart router coordinated",
      description: "Merge resolved — both agents unblocked on cart.py.",
      agentId: "agent_b",
      taskTitle: "Tax-inclusive checkout",
      filePath: CART_PATH,
    },
  ];
};
