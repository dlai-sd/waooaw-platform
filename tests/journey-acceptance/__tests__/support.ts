// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §8 Report content (shared test fixtures)
// Constitutional basis: C-059 (Implementation Traceability)
import type { Plan } from "../lib/plan.ts";
import type { ReportInput } from "../lib/report.ts";
import type { StepOutcome } from "../lib/types.ts";

export const samplePlan: Plan = {
  schema: "waooaw.journey-test-plan/v1",
  journey_id: "sample",
  version: 1,
  steps: [
    {
      id: "S1",
      title: "Discover",
      customer: "A",
      stimulus: "open",
      claims: [{ id: "S1-C1", statement: "offer shown", witnesses_required: ["W1", "W2"] }],
      proves: { gaps: ["PG-02"], requirements: ["WC107-R009"] },
    },
    {
      id: "S2",
      title: "Pay",
      customer: "A",
      stimulus: "pay",
      claims: [{ id: "S2-C1", statement: "paid", witnesses_required: ["W1", "W2", "W3"] }],
      proves: { gaps: ["PG-11"] },
    },
  ],
};

export function passed(stepId: string, identifiers: string[]): StepOutcome {
  return {
    stepId,
    title: stepId,
    verdict: "PASS",
    identifiers,
    reached: "L4",
    failurePath: false,
    witnessesRead: ["W1", "W2"],
    claims: [],
    retries: 0,
    reason: "",
  };
}

export function sampleInput(overrides: Partial<ReportInput> = {}): ReportInput {
  return {
    environment: "demo",
    plan: samplePlan,
    planDigest: "a".repeat(64),
    profileDigest: "b".repeat(64),
    commit: "c".repeat(40),
    services: [{ name: "web", image: "registry.example/web@sha256:" + "d".repeat(64) }],
    startedAt: "2026-11-23T10:00:00.000Z",
    finishedAt: "2026-11-23T10:05:00.000Z",
    outcomes: [passed("S1", ["PG-02", "WC107-R009"])],
    findings: [],
    providerModeFindings: [],
    syntheticVolume: { customers_created: 2, customers_removed: 2, left_over: [] },
    denominator: ["PG-02", "WC107-R009", "PG-11"],
    declaredLimits: ["Google first-login linking is not exercised"],
    ...overrides,
  };
}
