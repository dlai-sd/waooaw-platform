// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §8 Coverage And Depth Model
// Constitutional basis: C-059 (Implementation Traceability)
import assert from "node:assert/strict";
import { test } from "node:test";
import { depthByIdentifier, effectiveDepth } from "../lib/depth.ts";
import type { StepOutcome } from "../lib/types.ts";

function outcome(overrides: Partial<StepOutcome>): StepOutcome {
  return {
    stepId: "S1",
    title: "t",
    verdict: "PASS",
    identifiers: ["PG-01"],
    reached: "L4",
    failurePath: false,
    witnessesRead: ["W1", "W2"],
    claims: [],
    retries: 0,
    reason: "",
    ...overrides,
  };
}

test("depth never exceeds what the witnesses proved", () => {
  assert.equal(effectiveDepth(outcome({})), "L4");
  assert.equal(effectiveDepth(outcome({ witnessesRead: ["W1"] })), "L2");
  assert.equal(effectiveDepth(outcome({ reached: "L5" })), "L4");
  assert.equal(effectiveDepth(outcome({ reached: "L5", failurePath: true })), "L5");
  assert.equal(effectiveDepth(outcome({ verdict: "FAIL" })), "L2");
  assert.equal(effectiveDepth(outcome({ verdict: "NOT-WITNESSED", reached: "L1" })), "L1");
  assert.equal(effectiveDepth(outcome({ verdict: "FLAKY" })), "L4");
});

test("steps that did not run yield no depth", () => {
  for (const verdict of ["BLOCKED-BY-FLAG", "NOT-COVERED", "ENV-UNAVAILABLE"] as const) {
    assert.equal(effectiveDepth(outcome({ verdict })), null);
  }
  assert.equal(effectiveDepth(outcome({ reached: null })), null);
});

test("identifier depth is the deepest proven level, and unreached identifiers are NOT-COVERED", () => {
  const result = depthByIdentifier(
    [
      outcome({ stepId: "S1", reached: "L3" }),
      outcome({ stepId: "S2", reached: "L5", failurePath: true }),
      outcome({ stepId: "S3", identifiers: ["PG-02"], verdict: "BLOCKED-BY-FLAG", reached: null }),
    ],
    ["PG-01", "PG-02", "PG-03", "PG-01"],
  );
  assert.deepEqual(result["PG-01"], { depth: "L5", steps: ["S1", "S2"] });
  assert.deepEqual(result["PG-02"], { depth: "NOT-COVERED", steps: [] });
  assert.deepEqual(result["PG-03"], { depth: "NOT-COVERED", steps: [] });
  assert.deepEqual(Object.keys(result), ["PG-01", "PG-02", "PG-03"]);
});
